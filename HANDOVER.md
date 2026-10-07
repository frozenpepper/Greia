# Greia — Current Engineering Handover

**Updated:** 2026-10-07
**Canonical repository/branch:** `frozenpepper/Greia` / `main`
**Frozen baseline:** `372ee310f8e9a652bb88ecce75168e62928489e7` (clean tree)
**Version:** `0.13.0-phase0-dev`
**Primary blocking platform phase:** **post-R1 product-composition closure — T3-P OPEN/BLOCKING; install/update/release/multiplatform lifecycle now routes to `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md` (ADR 0036 successor). Gate-P5/V12G/D6 closure routing below is historical and superseded for lifecycle sequencing**
**Cross-hardware plan:** `docs/plans/2026-09-28_CROSS_HARDWARE_ROBUSTNESS_PLAN.md` — Tranche A → Acer end-to-end acceptance → Tranche U (UEFI) → Tranche B (capability matrix) → Tranche L (advisory lint)
**Current physical-hardware step:** **Fresh Acer first-boot FAILED and is source-repaired; run focused/full source acceptance, then REBOOT the build host to clear historical OPrdqB loop, build+flash a NEW legacy-x86-i686-dev USB, and repeat fresh first-installed-boot acceptance with no hotpatch/second boot**
**Public-source readiness:** **IN PROGRESS**
**Ordinary-family release:** **NOT READY**

This file is current-state routing only. Historical implementation detail belongs in Git history, dated reviews, testing records, and the append-only active architecture plan.

## 1. Start here

Read in this order:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-09-28_CROSS_HARDWARE_ROBUSTNESS_PLAN.md
docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md
HANDOVER.md
skills/greia-os-work/SKILL.md
```

Current install/update/release route: `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md` (ADR 0036 successor plan). The old signed `.greiaupdate` v2 / release-signing-key workflow is superseded by ADR 0036 and is historical only; Gate-P5/V12G/D6 closure routing in §§13–25 below is historical evidence, not the current next step.

Before installing/configuring tools also read:

```text
SETUP.md
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Do not use GitHub-hosted Actions without explicit owner authorization.

## 2. Platform state

Run R1 achieved the T0–T6 source tranche plus device-leg tranches 2 and 3, the forged-peer refusal restoration, and suite hardening (frozen at `372ee310`). That work is preserved, not repeated.

Evidence correction now in force (see the active plan entry of 2026-09-12 and the lifecycle-ledger correction of 2026-09-12):

```text
T3-S source composition primitives: DONE (source scope)
T3-P exact shipped product composition: OPEN / BLOCKING
T7: GREEN only in disposable/device-harness scope — not exact shipped service/unit proof
.greiabackup: absent
recovery media: absent
Parent encrypted/authenticated LAN transport: blocked (provisional HTTP)
historical Acer suite waiver: retained as history until an exact-head rerun replaces it
```

The current install/update/release work has completed **Session 02 of `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`** (ADR 0036 successor) for source scope — see §26. The `POSTR1-P1-INSTALLER-RED` (P1.1 installer composition RED) / Gate-P5 / V12G / D6 closure routing is historical and superseded for lifecycle sequencing; §§13–25 below preserve that Gate-P5 evidence as history. Do **not** start Raspberry Pi 400/500 work, UEFI work, destructive Acer installation, or R11 backup work outside the 2026-09-15 plan sequence, and do not treat T3 shipped product composition as complete. Do not discard or downgrade T7 evidence.

Current catalogue assertions must remain discovery-based. Do not freeze a first-party Activity count into new architecture or release gates.

The Parent authentication/runtime work below is a cross-cutting release-readiness tranche. It does not replace or skip the blocking product-composition closure above or later platform phases.

## 3. Parent client authority and frozen runtime

Maintained Parent browser source:

```text
frozenpepper/Greia-Parent-App-Html
```

Exact accepted Parent revision integrated into Greia:

```text
01301d285c6ba2a9a1f2948a9768b821d2536729
```

Production runtime chain:

```text
accepted Parent revision
  -> runtime/parent-app-client.toml
  -> runtime/parent-app-client.manifest.json
  -> vendor/parent-app/
  -> build/overlay/usr/share/greia-parent-app/
  -> /usr/share/greia-parent-app in the built image
```

Current pin contract:

```text
revision = 01301d285c6ba2a9a1f2948a9768b821d2536729
integration_state = vendored-image-integrity-enforced
```

The vendor and image-overlay copies are synchronized to that frozen Parent revision. The installed service verifies the browser runtime against the committed pin/manifest before serving it.

Future repins use only:

```bash
python3 tools/update_parent_client_pin.py \
  --parent-root /path/to/Greia-Parent-App-Html \
  --revision <exact-reviewed-parent-sha>
```

Do not manually advance the pin, manifest, vendor tree and image overlay as separate operations.

## 4. Parent authentication contract

The old human-entered shared `parent-pairing-token` model is retired from API-v1 and installed production.

Current flow:

```text
Parent enters Greia password once
  -> POST /api/v1/pairing/bootstrap
     {password, device_name}
  -> Greia verifies MainCredential locally
  -> Greia issues one revocable per-device credential
  -> browser stores only that device credential
  -> ordinary API requests use the device credential
```

Fresh-system credential remains:

```text
username: greia
password: greia
```

Parents can change that password from Parent management. Existing authorized browsers use independent device credentials and can be revoked separately.

Retired API-v1/production paths include:

```text
parent-pairing-token
X-Pip-Token
?token=<shared secret>
greia_parent=<shared secret> legacy cookie
pairing_token bootstrap input
filesystem-token retrieval as a user workflow
```

`ParentApiApplication` rejects those legacy transports and uses only device-scoped authorization. The older standalone `ParentStatusApplication` retains a separate compatibility token path for its legacy server only; that server is not production API-v1 authority.

The API-v1 wire names `/pairing/bootstrap` and `pairing_required` are compatibility vocabulary, not evidence that a shared token remains supported.

## 5. Authentication/runtime implementation state

Implemented in source and committed:

```text
password bootstrap -> per-device credential
independent Parent-device revocation
bounded failed-password limiter in production
legacy shared-token rejection in API-v1
stale legacy shared-token state retirement on API-v1 startup
real HTTP negative regression for X-Pip-Token / legacy cookie / query token / pairing_token input
separate legacy-status compatibility regression
API-v1 authentication ownership regression
exact Parent runtime revision pin
exact dependency-derived runtime manifest
synchronized vendor runtime
synchronized image-overlay runtime
installed-runtime integrity verifier
single-operation atomic Parent repin tool + regression coverage
```

The real HTTP negative regression is:

```text
tests/test_parent_api_legacy_token_negative.py
```

It proves retired shared-token transports fail at the actual API-v1 handler boundary and that only the supported device credential transports succeed.

## 6. Evidence boundary — do not overclaim

Already established from earlier owner-controlled evidence:

```text
PARENT SOURCE AT 01301d...:
  node syntax: PASS
  npm test: 77/77 PASS
  runtime_manifest.mjs: PASS

FIRST GREIA FROZEN ATTEMPT:
  stopped correctly at manifest comparison
  first failure was one stale src/views_activities.js digest
  stale digest was corrected without changing Parent runtime bytes
```

Current later Greia source state contains additional repin/authentication regressions. Those later tests have been **committed but not executed in an owner-controlled exact-current checkout in this connector session**.

Therefore current evidence remains:

```text
CURRENT GREIA FOCUSED AUTH/RUNTIME GATE: PENDING
CURRENT make verify: PENDING
OFFICIAL IMAGE BUILD FROM CURRENT DESCENDANT: PENDING
REAL BROWSER PASSWORD/RELOAD/CHANGE/REVOKE: PENDING
CURRENT PHYSICAL PARENT SYSTEM-CONTROL ACCEPTANCE: PENDING
```

A committed test is not a PASS.

## 7. One authoritative Parent acceptance protocol

Use only:

```text
docs/testing/2026-09-08_PARENT_UNIFIED_AUTH_RUNTIME_ACCEPTANCE.md
```

This is now the single execution authority for the Parent authentication/runtime tranche. It unifies:

```text
source identity
exact frozen Parent source tests
manifest regeneration + equality
9 focused Greia Parent suites
vendor + image-overlay integrity
make verify
canonical image build
installed runtime integrity
LAN discovery
default-password bootstrap
wrong-password rejection
browser credential persistence
Parent password change
independent device revocation
fresh rebootstrap after revocation
real HTTP rejection of every retired shared-token transport
production service sandbox sanity
physical volume/Wi-Fi/SSH/other advertised setting checks
profile/Activity-policy smoke test
owner-state restoration
final transport-security blocker and report
```

The older files remain historical only:

```text
docs/testing/2026-09-08_PARENT_PASSWORD_RUNTIME_INTEGRATION_ACCEPTANCE.md
docs/testing/2026-09-02_PARENT_REAL_RUNTIME_FINAL_ACCEPTANCE.md
```

Do not combine their obsolete token instructions with the unified procedure.

## 8c. Acer Wi-Fi / installer UI / CPU spin — source fixes landed, awaiting owner hardware evidence (2026-09-28)

Source fixes are complete, regression-locked and pushed. The physical acceptance
is **not** yet obtained. Root causes: `docs/INSTALLATION_ISSUES_LOG.md` §§14–16.

```text
§13 wireless ownership   iwd owns wireless; networkd Unmanaged=yes
§14 Wi-Fi shows nothing  empty scan was latched as READY, and a real scan error
                         was masked as "No networks found". Empty scans now
                         retry (limit 4, settle delay) and errors are surfaced.
                         Proven NOT to be iwd/driver: the backend returned 5 real
                         networks when run directly on the Acer.
§15 Pointer page broken  layout assumed font metrics AND the fit arithmetic
                         omitted the header entirely. Header, row floor, strip
                         label and tail are now measured; a row can never be
                         shorter than its own label. At 600 px the test strip is
                         dropped whole rather than colliding with Back/Continue;
                         the 1 2 3 keys still run the same test.
§16 ~97% CPU spin        boot-cover helper retried every 0.5 s forever because it
                         wrote to root-owned /run/greia-os as User=nobody.
                         2754 spawns in one boot. Marker moved to the runtime dir
                         the unit owns; retry now capped with backoff.

preflight:  68/68 focused + 80/80 broader affected sweep
evidence:   SOURCE-CLOSED (source + regression locks)
            all three fixes re-verified on the live Acer (render, wifi=5,
            helper rc=0 as nobody) but NOT yet on a freshly built image
next:       IMAGE BUILT + USB FLASHED 2026-10-01 (§8e); owner boots the stick
            on the Acer and reports the first visible boot stage
```

Still open and **not** addressed by this tranche:

```text
installed first boot from the Acer internal disk   never yet exercised end to end
build-host loop leak per image build                OPEN build-host cleanup defect
```

The loop leak accumulates one autoclear loop per image build and only clears on
a host reboot. It does not affect a correctly flashed USB.

## 8d. Cross-hardware robustness plan created; Acer route continues first (2026-09-28)

The 2026-09-28 Acer defects were analysed as ten recurring **classes** rather
than machine bugs, each researched for known instances on other hardware and
sequenced for removal in `docs/plans/2026-09-28_CROSS_HARDWARE_ROBUSTNESS_PLAN.md`.

```text
C1 undeclared resource ownership      C6 advertised != real capability
C2 environment-metric assumption      C7 runtime mutation lost on re-enumeration
C3 latched or unbounded failure       C8 identity / name instability
C4 failure masked as a benign state   C9 probe identity != service identity
C5 silent under-provisioning          C10 single-machine evidence
```

Approved scope and ordering:

```text
Tranche A  generalise the actively-wrong Acer shapes (A1 storage modules from
           the real target device, A2 panel-sized boot art, A3 DWT keyboard
           pairing, A4 pointer property re-application)
  then     Acer end-to-end acceptance  (inserted ahead of the approved order;
           the installed path has never been exercised and C5 bites there)
  then     Tranche U  UEFI, amd64 first (BOOTX64.EFI live + x86_64-efi target),
           IA32 BOOTIA32.EFI as a legacy-niche follow-on
  then     Tranche B  synthetic capability matrix: hardware becomes a test input
  then     Tranche L  advisory lint for hardware-shaped assumptions (report only)
```

**Biggest latent risk, C5:** the storage-module set is the fixed triple
`("ahci","libata","sd_mod")` in both `greia-storage-modules` and
`_verify_installed_initramfs_storage`. Because the hook probes with `modinfo`, an
NVMe / SAS / Intel RST / USB / MMC root gets nothing added and the install guard
passes **vacuously** — the same class that grey-screened the Acer after
installation. Tranche A1.

**Biggest structural gap:** 11 profiles exist — 7 i386, 4 amd64, **0 arm64**, all
legacy BIOS + Syslinux. `pi-400-v1`, `pi-500-v1`, `pi-mbr-tryboot-ab-v1`,
`pi-tryboot-ab-v1`, `pi-live-usb-v1` and `modern-gpt-ab-v1` are in the schema but
no profile exercises them, so **no UEFI-only machine can boot a Greia installer**
and the first-class ARM references cannot be built. Tranche U.

Recorded as **already correct, do not "fix"**: `hal_legacy_x.py` resolves XInput
properties by name (atom IDs are device-specific: 275 vs 304 on real touchpads),
and `REFERENCE_WIDTH`/`REFERENCE_HEIGHT` are scale denominators and defaults, not
hard layout dependencies.

Evidence: the plan and research are **SOURCE-CLOSED**. No tranche is implemented.

## 8e. Image rebuilt and USB flashed; the build had been broken on `main` (2026-10-01)

Synced first: `HEAD == origin/main == 439a9060`, 0 ahead / 0 behind.

The `legacy-x86-i686-dev` build then **failed**, and the cause was already on
`main`. `e859fb4b` ("Build and install the microphone processing endpoint
plugin", 2026-09-30) put an unscoped

```bash
chmod 0755 "$rootfs/usr/local/lib/greia-os/greia-audio-endpoint-probe"
```

at the top of `compose_configure_systemd` in `build/lib/compose.sh`, above the
`if [[ "$role" == "target" ]]` branch. The probe ships only in `build/overlay`;
the live-installer role composes from `build/installer-overlay`, which has no
such file, so under the builders' `set -e` **every** installer build aborted on
the live leg before publishing an image. The installer role does not want the
file either — `greia-audio-endpoints.service` is enabled only in the `target`
branch — so the chmod now sits inside that branch and the 203/EXEC repair the
original entry added is preserved for the root that needs it.

Rebuilt and flashed through the physical front door
`tools/build-and-flash-development-usb.sh legacy-x86-i686-dev /dev/sdc` onto
the owner-returned LaCie iamaKey (serial `eca3505216d7d3`), unmounted and
identity-checked before the write:

```text
source_artifact_verification=PASS
usb_flash_readback_verification=PASS   (usb_readback_verification=PASS)
boot_writer=postmortem-proven-syslinux-fat32
image sha256=9bfe662cea6c57f7e657f0ce3a0edc393fc4cdc2f251531b9775571b14883a09
live_media_id=e21e7bca-baab-48b4-b920-81880067395c   (read back off the stick)
boot_artwork_mode=full-color-landscape-canvas-v1  canvas=1600x900  grub=padding-centered
```

`tests/test_image_staging_contract.py` 19/19.

Evidence lane is **VM/IMAGE + written USB medium only**. The Acer has not booted
this image; do not report it as hardware-accepted. Record the first visible boot
stage when it does.

Two things carried forward, neither introduced here:

```text
accounted installed filesystem use 984 MiB   over the C0 preferred <=800 MiB,
                                            under the required <1,000 MiB target
test_system_overlay_contract.py  1/23 FAIL   pre-existing on 439a9060 (verified with
                                            the fix stashed): tmpfiles overlay says
                                            group pipprofiles where the test and
                                            AGENTS.md say greiaprofiles
build-host loop leak per image build         one autoclear loop left from this build
```

## 8f. Fresh install restart-looped; both provisioning defects closed at source (2026-10-01)

The appliance installed from today's image (`sha256=9bfe662c...`) restart-looped
on first boot. `greia-launcher.service` read `active` between restarts;
`NRestarts` climbed past 21.

**Defect 1 — `/run/greia-os` resolved to `root:root 0755`.** Two tmpfiles files
declared the path, and `/usr/lib/tmpfiles.d` sorts after `/etc/tmpfiles.d`, so
`greia-os-runtime.conf` silently overrode the correct owner of record in
`greia-os.conf` (`0770 greiakid pipprofiles`). Xorg runs as `greiakid`, could not
create `Xorg.0.log`, and xinit exited 1. The boot-marker spool is in the same
directory, so the loop was mute. Duplicate declaration removed; the test that
required it rewritten; a cross-file contradiction guard added and verified to bite.

**Defect 2 — the child's profile tree was created by the Parent.** `data/` and
`data/<id>` were `greiapel:pipprofiles 2750`, so `greiakid` could not create its
own `progress` directory and `child_shell` died before READY. The B3 repair in
`first-boot` handles this but is ordered `Before=greia-parent`, while the Parent
is the creator — so on a fresh install the repair was skipped and only took
effect on the **second** boot. `first-boot` now pre-creates the data root as
`greiakid:pipprofiles 2770`, which is the one place that runs as root ahead of
the Parent. B3 retained for upgrades. Locked by a new test.

```text
device        PHYSICAL, greia-dev @ 10.42.0.203 (greia/greia)
after repair  launcher_interactive_ready, NRestarts=0 on launcher/parent/audio,
              Xorg.0.log present, greiakid writing its own progress/
NOT yet       the image has NOT been rebuilt; a fresh install from the current
              stick will still loop. Rebuild + physical re-acceptance are owed.
make verify   3841 tests, 15 failures, byte-identical set to the pre-existing
              15 at 439a9060 (diffed); none in the suites this change touches.
```

## 8. Current exact next step

Session 03 source implementation and source validation are complete for the
current owner-release CLI tranche. The corrected validation reported:

```text
3601 tests OK
4 skipped
make verify PASS
project validation PASS
footprint PASS
clean-bytecode PASS
```

The source/test delta that fixed the only first-run failure is
`dc36cfc93f01d5a9a3085421c499aa5b6d3c3e62`; the following commits before
the validation-routing update were documentation-only. No production release
or build behavior changed after that fix.

The exact current lifecycle step is the **Session 03 Linux owner-release build
acceptance**:

```text
docs/testing/2026-09-21_SESSION03_LINUX_RELEASE_BUILD_ACCEPTANCE.md
```

Run it only on an owner-approved x86_64 Linux build host. It intentionally
permits the production build command's debootstrap/chroot/mount activity but
forbids physical-media writes, manual mount/loop surgery, QEMU, Docker,
physical Acer installation, and source edits during the frozen run.

The acceptance-defining operation is the single owner command:

```bash
sudo python3 tools/greia_release.py build \
  --version "$(cat VERSION)" \
  --output <project-local-output>
```

It must produce the current Greia release directory with the real
`acer-aspire-one-i386-ab.greiaupdate`, compact intermediates and a
source-bound `release-report.json`. The universal Setup image remains
explicitly deferred to Session 08; Session 03 is not an installer-image
acceptance.

If that Linux owner-command build is green, Session 03 closes and Session 04
opens. Session 04 then proves the legacy i386 lifecycle using the real bundle.
The Parent unified acceptance remains its own cross-cutting release-readiness
tranche and is not the current blocking lifecycle step.

## 8b. Session 02 repair tranche R2 — source complete, physical gates owner-side (2026-09-18)

> HISTORICAL — NOT CURRENT ROUTING. The R2 owner-operated hardware path below
> was cancelled by explicit owner decision ("cancel with record", T-BAG R2
> `abandoned`; see §§"2026-09-18 — R2 RETIRED" below). No owner hardware run
> is required to finish R4: R4 is an autonomous source-only repair tranche and
> all physical acceptance stays DEFERRED under the new authoritative closeout
> in §30. The `docs/handovers/TBAG-opencode2-plugin-handoff/` directory
> referenced below has been deleted; that reference is retained as history
> only. "Session 03 must not begin until the owner completes them" and "Exact
> owner next steps" are superseded by §30 — Session 03 status is owned by the
> lifecycle plan ledger, not by this section.

Run R2 executed `GREIA_SESSION02_REPAIR_LOCAL_AGENT_PLAN.md` (Session 02 review contradictions, Repairs A–J plus triage amendments). All implementation/review/integration closed through the T-BAG loop with fresh reviewers:

```text
T01 Acer A/B 1536 MiB profile + capacity regression      integrated
T02 composer-owned clone neutrality                       integrated
T03 shared fstab renderer + finalizer UUID specialization integrated
T04 candidate hardware-support archive drives finalization integrated
T05 Installed-Size (not .deb bytes) capacity accounting   integrated
T06 updater CAP_SYS_ADMIN+CAP_SYS_CHROOT contract          integrated
T07 PERSIST fallback marked provisional (Session 04 owns) integrated
T08 streaming payload compression/verification            integrated
T09 Acer A/B profile identity in release path             integrated
T10 retired X-Pip-Token production path                   integrated
T12 payload-stage clone-neutrality gate                   integrated
T14 installer-unit stale wording cleanup                  integrated
T16 fstab mode alignment                                  integrated
T17 release-workflow headroom docs                        integrated
T18 final verification sweep                              accepted PASS
```

Committed as `5bd8c6e3` (wave 1) + `ab3c4c4e` (wave 2) + `e9fe5044` (wave 3);
tree clean. Phase gate (×3 auditor passes) verdict: source scope consistent,
exit predicates requiring Orbiter artifact evidence (§16), exact-service
staging proof (§17) and physical Acer acceptance (§18 + §23 DoD) remain
UNPROVEN — Session 03 must not begin until the owner completes them.

Exact owner next steps (repair plan §§16–18): Orbiter clean-Linux build of
the Acer target root + relocatable payload + `.greiaupdate` inspection with
headroom calculation, then Acer fresh install → A→B update through the
exact installed service → candidate boot/accept → failure-recovery smoke.
Return artifact sizes/headroom/service logs per §24; they close the phase.

Run state: `TBag/runs/R2` (active). OpenCode 2 TUI status plugin fixed and
verified in-project (see the deleted `docs/handovers/TBAG-opencode2-plugin-handoff/`
— HISTORICAL reference only, directory removed);
autonomous parent wakes never arrive in this setup (heartbeat enrolls, timer
and prompt delivery unverified host-side — documented there, skill RC60
committed in the skill dev checkout, not pushed).

## Historical Gate-P5 evidence (§§13–25) — superseded lifecycle routing

The sections below (footprint reduction, apt-cache ports, Gate-P5/V11–V12G
closure attempts, D1–D6 defect records) are preserved historical evidence.
Their embedded `Next:` lines pointing at `POSTR1-P5-GATE-CLOSURE-*` /
V12x / D6-repair successors are superseded: current lifecycle sequencing
comes from `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`
(ADR 0036). Any signed `.greiaupdate` v2 bundle, release signing key,
`trusted-keys/*.pem`, `seq*/signature-verified`, `verify_update_signature`
or `python3-cryptography` release-verification wording below describes the
old experimental signed flow superseded by ADR 0036, not the normal
production route.

## 13. Footprint composition reduction (2026-09-13) — `POSTR1-P5-FOOTPRINT-REDUCE`

Build-hygiene-only change, no Phase-0 product scope removed, no bound raised or weakened:

- `build/build-image.sh`: before manifest/footprint capture, purge orphaned build-toolchain `binutils`, prune unused `cc1`, prune base non-`en*` gettext locales, prune base man/info and non-copyright doc files (disposition `POSTR1-P5-FOOTPRINT-DISPOSITION` rows 1–4; row 5 Perl/media-types and row 6 WAV→OGG not applied).
- Source: worktree commit `4379de64` (only `build/build-image.sh`, +32 lines); profile `acer-aspire-one-i386-ab.toml` unchanged (800 preferred / 1000 required / 1250 review).
- Measured on the owner-provisioned orbiter lane, official `build/build-installer-image.sh acer-aspire-one-i386-ab` with V8-pinned bundle/key inputs [historical signed v2 flow, superseded by ADR 0036] (`greia-release.greiaupdate` sha `e20895a0…`, `trusted-keys/greia-release-main.pem`): target gate **PASSES** with `installed 981 / filesystem-used 981 / accounted 981 MiB < required 1000` (red baseline was 1080; reclaim 99 MiB; preferred ≤800 still unmet by honest disposition — warning only, no child scope cut to chase it). Full installer image built: `greia-os-installer-acer-aspire-one-i386-ab.img` (1257 MiB USB, sha `93c0fda9…`, payload squashfs sha `e5b3818d…`).
- Mechanism proved on the shipped payload (mounted read-only): `cc1` absent, `binutils` absent from package manifest (`cpp-12`/`x11-xserver-utils` intact), locales `en*` only, man/info empty, docs copyright-only; preserved scope verified: `xinit`/`xrandr`/`xinput`/`bwrap`, `Xwrapper.config` (`allowed_users=anybody`, `needs_root_rights=yes`), `python3-pygame`/`python3-pil`/`fonts-noto-color-emoji`/`bubblewrap`/`xserver-xorg-legacy`/`openssh-server`/`sudo` in manifest, 41 activities incl. `writing`+`painting`, `import pygame` 2.1.2 OK in payload chroot, A/B bundle + `installer-ab.env` (`DEVELOPER=0`) on the medium.
- Local `make verify` PASS at the change (3367 tests OK, skipped=3; validate/shell-check/footprint clean).
- Evidence: T-BAG attempt dir `POSTR1-P5-FOOTPRINT-REDUCE/attempts/implementer-1/` (`evidence.tgz` sha `839192bd…`, orbiter log `/tmp/greia-p5-reduce-build.log`, out `/tmp/greia-p5-reduce-out/`).
- Next exact step: `POSTR1-P5-GATE-CLOSURE-V9` re-attempts the live nine-predicate closure against this official image. Margin note for planning: 19 MiB under required; optional Perl/media-types cut (row 5, ~40 MiB, needs pygame import re-proof) remains available if headroom is wanted — not this task's scope.

## 9. Parent/API ownership boundaries

Primary current owners:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
vendor/parent-app/
build/overlay/usr/share/greia-parent-app/
tools/update_parent_client_pin.py
src/greia_parent/static_client.py
src/greia_parent/parent_client_integrity.py
src/greia_parent/password_auth.py
src/greia_parent/protocol.py
src/greia_parent/api_server.py
src/greia_parent/package_api.py
src/greia_parent/update_api.py
src/greia_parent/production_api.py
src/greia_platform/main_credential.py
tests/test_update_parent_client_pin.py
tests/test_parent_api.py
tests/test_parent_api_legacy_token_negative.py
tests/test_parent_auth_ownership.py
tests/test_parent_legacy_status_auth.py
```

The Parent HTTP process remains unprivileged. Never solve unavailable functionality by giving it generic root/sudo/shell authority.

Production Wi-Fi remains fail-closed: real iwd only, and `network.manage=false` when the installed unprivileged composition cannot genuinely manage it.

Speaker volume/mute remains a typed desired-state path. The Parent HTTP process does not own ALSA; the child hardware session applies system-control state.

## 10. Remaining Parent release blocker

Current transport remains provisional HTTP.

Password bootstrap fixes the product authentication model, but Parent password and device bearer credentials are not ordinary-family release-safe over unauthenticated plaintext LAN transport.

Ordinary-family Parent release therefore remains blocked until Greia has accepted:

```text
authenticated encrypted transport
Greia endpoint/device identity
reviewed trust/onboarding lifecycle
```

The solution must preserve the simple Parent-password workflow. Do not reintroduce hidden filesystem tokens, mandatory QR/PIN ceremonies, or ad-hoc custom application crypto as a workaround.

## 11. Evidence discipline

Always distinguish:

```text
SOURCE REVIEW
LOCAL AUTOMATED TEST
BROWSER
SIMULATOR
VM / IMAGE
PHYSICAL DEVICE
```

A successful HTTP response is not proof that physical hardware changed. A later SHA does not inherit earlier physical evidence unless the relevant bytes and acceptance contract explicitly establish equivalence.

## 12. Owner waiver (2026-09-12) — preregistered pre-intro timing comparison DEFERRED for Gate P3 (`POSTR1-P3-TIMING-WAIVER-RECORD`)

Owner authority: `TBag/runs/R1/authority/decisions/postr1--POSTR1-P3-PREINTRO-TIMING-MEASURE--001.md` (2026-09-12; owner intent: functionality first — "lets have everything working, then we will work on shaving seconds in a later stage").

- The preregistered pre-intro timing comparison (P1–P4 predicates) is DEFERRED and waived for Gate P3 / `UPDATE_PRODUCT_COMPOSED`. It was not measured and is not proven.
- This task supersedes `POSTR1-P3-PREINTRO-TIMING-MEASURE`, which never passed: no QEMU baseline/activated boot occurred and no measurement record exists. No measurement is fabricated or interpolated here.
- The red timing predicate stays red and parked: waived by explicit owner authority for the P3 gate, not proven and not narrowed by workers.
- Gate P3 no longer depends on the P1–P4 comparison. Blocked downstream work (`POSTR1-P3-UPDATE-ACTIVATION` integration, `POSTR1-P3-UPDATE-PROOF2`) may proceed without the timing evidence.
- The fixed 7.0 s intro (5 s animation + 2 s hold) and the frozen P1–P4 predicate definitions remain unchanged; only their scheduling/ownership changes.
- Re-ownership obligation: the timing proof must be re-owned by the later boot/performance stage plan before release certification.

## 14. Persistent apt/pool cache port (2026-09-13) — `POSTR1-P5-APTCACHE-PORT`

Source port of the persistent apt-cache behavior onto the current
footprint-hygiene builders (orbiter reference `e36dd148` unreachable from this
lane; behavior reconstructed from the task brief):

- New `build/lib/apt-cache.sh` (`GREIA_APT_CACHE=/var/cache/greia-apt`,
  `GREIA_POOL_CACHE=/var/cache/greia-pool`; `mount_apt_archives_cache` /
  `mount_pool_cache` bind-mount + print mountpoint).
- `build/build-image.sh`: sources helper, bind-mounts the apt cache after the
  `/run` tmpfs + resolver stub into `MOUNTS`; `apt-get clean` → `autoclean`,
  drops only the `archives/*.deb` removal term.
- `build/build-installer-image.sh`: sources helper, bind-mounts apt + pool
  caches into `MOUNTS`; same `autoclean`/lists-only cleanup; existing
  pre-`mksquashfs` `safe_unmount_paths` releases both before compression.
- `build/install-live-hardware-firmware.sh`: `clean` → `autoclean`.
- `build/populate-hardware-support-pool.sh`: `POOL_CACHE_IN_CHROOT` (default
  `/var/cache/greia-pool`) + `POOL_CACHE_HOST` (default
  `$LIVE_ROOT$POOL_CACHE_IN_CHROOT`, so standalone unmounted runs stage the
  same pool); both `Dir::Cache::archives=` point at the in-chroot cache;
  post-loop in-chroot `autoclean`, then copy `*.deb` into a fresh `POOL_DIR`
  before `finalize_hardware_support_pool.py`.
- Contract test `test_builds_share_a_persistent_apt_cache_instead_of_redownloading`
  in `tests/test_system_overlay_contract.py`; docs in
  `docs/agents/GREIA_AGENT_OPERATIONS.md` (§12, never-clear rule) and
  `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` (§11, rebuild reuse).
- No profile/package-set/limit/gate/installed-content change; footprint-hygiene
  block and A/B installer wiring intact.
- Verification: four focused suites green; `bash -n` + `make shell-check`
  clean; full `make verify` result recorded in the attempt report.

## 15. Apt-cache debootstrap-era .deb fix (2026-09-14) — `POSTR1-P5-APTCACHE-FIX`

Source fix for the mount-after-debootstrap trap: `build/build-image.sh` and
`build/build-installer-image.sh` now bind-mount the persistent apt cache
BEFORE `debootstrap` so base `.deb`s land in the host cache
(`GREIA_APT_CACHE`) instead of the real target/live directory; pool-cache
mount moved with it on the live root. `build/lib/apt-cache.sh` header and
both cache docs now mandate before-debootstrap mounting. Contract test
`test_builds_share_a_persistent_apt_cache_instead_of_redownloading`
strengthened to assert `mount_apt_archives_cache < debootstrap --arch= <
apt-get` on both builders. Fast path preserved (`autoclean`, no `clean`, no
host-cache clear, `MOUNTS` teardown intact); footprint-hygiene block and A/B
wiring untouched. Verification: 23/23 overlay-contract + pool/live/installer
suites green; full `make verify` 3368 OK (skipped=3); validate/shell-check/
footprint clean. Real-image proof deferred to `POSTR1-P5-APTCACHE-REPROOF`.

## 16. Gate-P5 closure attempt V11 (2026-09-14) — RED, Gate P5 OPEN, T3-P OPEN, escalated product defects

Orbiter lane recovered and fully capable; official `acer-aspire-one-i386-ab` image rebuilt (footprint 981/981/981 PASS) and boots. Six live closure attempts ran real product legs; 0/9 predicates GREEN. Harness fixes inside worker scope (squashfs host-rebuild, ctl snapshot, IDE+kvm:tcg, clone serial console, live transaction-socket bridge; all unit-green) are committed in the task worktree. Two shipped-product defects block the gate and need product authority: (D1) socket activation spawns `greia-install-transaction.service` without `LISTEN_FDS` (in-guest serial proof; install impossible); (D2) `greia-system-update.socket` is never enabled/started anywhere (payload lacks the wants-link; no puller), so update/recovery legs cannot run even after D1. Evidence: T-BAG `POSTR1-P5-GATE-CLOSURE-V11/attempts/implementer-1/` (report + evidence/). Next: product fix D1+D2, official rebuild, closure re-run. T3-P remains OPEN/BLOCKING.

## 17. Gate-P5 closure re-run V12C (2026-09-14) — continuation (Gate P5 OPEN, T3-P OPEN)

V12B implementer lane wedged (poisoned resumable session; owner re-issued identical brief as V12C, V12B superseded). V12C re-derives V11's four harness behaviors as code-only against current primary (frozen `HANDOVER.md` hunk not applied; history append-only): clone-only serial-console prepend, clone-only transaction-socket wants-link, squashfs rebuild into host work_dir, control-disk/installer `snapshot=on` + explicit `ide-hd` placement + `pc,accel=kvm:tcg`, plus the `gate_p5` boot-perf timeout binding; three focused `tests/test_x8_qemu` suites re-proven green before any orbiter run. Depends on integrated `POSTR1-P5-SOCKET-ACTIVATION-FIX` (D1+D2: native `LISTEN_FDS` + fd 3 on all three services, `greia-system-update.socket` enabled in `build/build-image.sh`; reviewer-1 PASS). Next: clean-archive delivery to orbiter, official installer rebuild with both A/B env vars, single full `run_gate_p5_closure_product()` with seeded `d31_fn` and P5.4 baseline; T3-P DONE if and only if all nine predicates GREEN.

## 18. Gate-P5 closure re-run V12C (2026-09-14) — RED, Gate P5 OPEN, T3-P OPEN, new shipped defect D3

Official image rebuilt from HEAD `135d4b85` (socket-fix + re-derived harness): `greia-os-installer-acer-aspire-one-i386-ab.img` 1318060032 B, sha `2893e0d5…`, payload `8569f8e2…`, footprint 981 PASS. D1+D2 confirmed fixed IN the built image (both socket wants-links present in target payload; zero `^StandardInput` on all three shipped units). Closure run on orbiter: positive control RED-as-expected (`d31_fn=None` → BLOCKED), then the real install-prepare leg failed red — guest boots to login, socket listens, control dials, but `greia-install-transaction.service` dies on every activation (5× spawn → `service-start-limit-hit`), guest never powers off, host leg times out. Root cause (host-side chroot proof against the run clone's own live bytes, sensitivity-controlled): D1 gate now PASSES, but `ServiceState.from_target_profile` raises `target image profile misses release facts` — shipped live `/etc/greia-os/target-image-profile.json` carries `profile.profile_id` while service AND client both contract `profile.id` (writer `BuildProfile.declared_manifest` serializes the dataclass field name; contract suites mask it with hand-written `id` fixtures, 38/38 + 10/10 green). D3 predates this delta (all implicated files byte-identical to primary; reader dates to 8A-era; masked in V11 by D1) and its files sit outside this task's Allowed changes, so no repair was attempted — product/build authority must decide writer-vs-reader ownership. One lane-hygiene note: orbiter's persistent pool cache held a stale `libssh2-1_1.10.0-3+b1` duplicate that failed the first build at pool finalize; only that stale file was removed (58 cached debs scanned, no other duplicates), rebuild GREEN. Evidence: T-BAG `POSTR1-P5-GATE-CLOSURE-V12C/attempts/implementer-1/` (report + evidence/ + SHAs). Next: product fix D3 (profile-manifest `profile.id` contract), official rebuild, closure re-run. T3-P remains OPEN/BLOCKING.

## 19. Gate-P5 closure re-run V12D (2026-09-14/15) — BLOCKED, orbiter lane inaccessible after worker-caused host unmount; Gate P5 OPEN, T3-P OPEN

V12D implementer validated everything reachable, then lost the lane before any closure leg ran. Pre-orbiter: HEAD `210d377b` carries the D3 `profile.id` contract fix (writer `tools/build_profile.py:621`, readers aligned, `src/greia_installer/` untouched) plus the carried V12C harness delta; focused suites green (`test_product_install` 38, `test_product_boot_health` 44, `test_product_recovery_d31_reverse` 31) and dependency surface green (contract 6, build-profiles 8, update-unit 15, transaction-service 38, developer-remote 32). Orbiter lane verified healthy (`SSH_OK`, `sudo -n whoami` → root); V12C image (bound to pre-fix `135d4b85`) treated as absent; clean archive of `210d377b` (sha `5af77ee9…`) delivered to `/tmp/greia-p5-v12d-src`; V8 bundles/keys reused as recorded inputs; closure driver `/tmp/greia-p5-v12d-closure.py` written (V12C two-phase shape, pinned HEAD, frozen P5.4 baseline, positive control first; syntax-checked on orbiter, never executed). Partial build evidence (transcribed): payload manifest carries canonical `profile.id`, footprint 981 PASS.

Incident (worker-owned): after killing a misconfigured build (first attempt fail-closed — exported `GREIA_AB_*` stripped by sudo `env_reset`; env must ride on the sudo command line), cleanup ran raw `umount -R` against a chroot with shared-propagation host bind mounts; host `/dev`+`/proc`+`/sys` were unmounted (`/dev/null` became a regular file, `/dev/loop*` gone). `/proc` remounted OK and `/sys` was still mounted, but `/dev` recovery was inconclusive and minutes later new ssh fails deterministically (TCP accept then RST; ping OK, port 22 open). Only the worker's own SIGKILL debris was removed (loop63, 2 build dirs, partial out dir — verified); all pre-existing residual loops left untouched per lane policy. No project source modified (worktree clean). No closure leg, positive control, predicate, or SHA binding was executed: 0/9 UNEXECUTED (not red). Evidence: T-BAG `POSTR1-P5-GATE-CLOSURE-V12D/attempts/implementer-1/` (report + `v12d-status.json`); orbiter-side artifacts marooned in `/tmp/greia-p5-v12d-*` pending lane recovery. Next: owner/parent restores orbiter via console (reboot drops residual loop bindings — re-record `losetup -a` after), then rebuild with sudo-command-line env and run the on-disk driver; never `umount -R` a build chroot with host bind mounts. T3-P remains OPEN/BLOCKING.

## 20. Gate-P5 closure re-run V12E (2026-09-15) — RED, Gate P5 OPEN, T3-P OPEN, new shipped defect D4

V12E implementer re-ran the full closure on the owner-restored orbiter lane at HEAD `0afa1b96` (R01-03 ops notes only; D3 fix + V12D-carried harness delta integrated). Lane healthy; orbiter `/tmp` held no V12D residue so all artifacts rebuilt. Official `acer-aspire-one-i386-ab` image rebuilt from this HEAD (1318060032 B, sha `036f6ea9…`, footprint 981 PASS; keys/bundles re-minted through production builders, seq20/21/23 signature-verified). D3 verified fixed IN the built artifact (payload and live `target-image-profile.json` both carry canonical `profile.id`); D1+D2 intact in the image. Closure run: positive control RED-as-expected, then the real install-execute leg timed out (guest boots to login, never powers off) — 0/9 predicates GREEN. Journal-to-console replay on a disposable copy of the run clone isolates new shipped defect D4: the install-transaction service dies verifying ANY release signature (`release signature is not trusted: Ed25519 … requires python3-cryptography` ← no `cryptography` module in the built live root; live manifest confirms absence). Composition cause: the A/B profile omits package-set `system-update` (header defers inclusion pending measured/accepted C0 footprint delta) while shipped install/update services fail-closed require it — a product/build-authority decision outside this task's Allowed changes, so no repair attempted and no clone-side injection (that would be harness substitution). Own mounts/loops cleaned (single unmounts only); key/sudoers plus one pre-existing stuck deleted-file loop left for parent/owner. Evidence: T-BAG `POSTR1-P5-GATE-CLOSURE-V12E/attempts/implementer-1/` (report + `v12e-status.json` + `closure.log` + `diag-execute-serial.log`). Next: product/build authority accepts the `system-update` set for the A/B profile (verify i386 installability + footprint delta), official rebuild, closure re-run. T3-P remains OPEN/BLOCKING.

## 21. `system-update` set selected for the A/B profile (2026-09-15) — `POSTR1-P5-SYSTEM-UPDATE-INCLUSION`

Composition decision (product/build, ADR 0013; the A/B profile is exactly the profile the `system-update` set header anticipated): `acer-aspire-one-i386-ab` now selects `system-update` (`python3-cryptography`) in `target_sets` (installed update/recovery verification via `SystemUpdateService.verify` → `_cryptography_ed25519`) and in `installer_sets` (live release verification via `fresh_ab_install` → `verify_update_signature`); all single-root/dev profiles still omit it. Resolves Gate-P5 blocker D4. No bound raised, no Phase-0 scope removed.

- i386/bookworm closure proven on orbiter (disposable chroot, since removed): candidate `python3-cryptography 38.0.4-3+deb12u1` (`pool/main/p/python-cryptography/python3-cryptography_38.0.4-3+deb12u1_i386.deb`, sha `78a69c1c…`, Installed-Size 3070 KiB; closure `python3-cffi-backend` 207 KiB + `libssl3`/`libc6`/`libgcc-s1`/`python3`); `apt-get install` exit 0, `import cryptography` 38.0.4 + Ed25519 sign/verify OK.
- Official rebuild from source HEAD `16fdbedd` (archive sha `e2ee65c0…`; `GREIA_AB_*` on the sudo command line; bundle input reused V12E seq20 `ad7e4e39…`, trusted key `f9814ae9…`): target footprint `installed 985 / filesystem-used 985 / accounted 985 MiB < required 1000` — gate **PASSES** (delta +4 MiB vs the 981 baseline; preferred ≤800 warning honestly retained). Installer image `greia-os-installer-acer-aspire-one-i386-ab.img` 1320157184 B (1259 MiB USB) sha `e51f24e0…`; payload squashfs sha `03fbcc35…`; USB bundle == input seq20; target manifest sha `f4ca5474…`, installer manifest `1db2706a…`.
- Built-artifact proof (read-only USB mount + unsquashfs of both squashfs): live AND target package manifests carry `python3-cryptography 38.0.4-3+deb12u1`; live AND target chroots `import cryptography` 38.0.4 + Ed25519 OK; production `verify_update_signature` inside the built live bytes verifies the real bundle (`greia-0.20.0`, profile `acer-aspire-one-i386-ab`) — the exact D4 call is now GREEN at artifact level.
- Regression: `test_ab_profile_selects_system_update_in_both_scopes` in `tests/test_build_profiles.py` (positive control: selection removed → 1 failure RED; restored → 9/9 GREEN). Local full suite 3386 OK (skipped=3) at the composition commit.
- Honest notes: live security-support report carries a pre-existing binutils trusted-content notice (live-root build-toolchain residue, unrelated to this change); target `security_support_state=no-alerts`. Orbiter lane left clean (single unmounts only, loop detached, no `umount -R`); key/sudoers plus pre-existing snap loops untouched for parent/owner.
- Orbiter evidence: `/tmp/greia-p5-sysupd-out/` (image + reports), `/tmp/greia-p5-sysupd-build.log`, `/tmp/greia-p5-crypto-proof.txt`; source archive `/tmp/greia-p5-sysupd-src.tgz` (sha `e2ee65c0…`). T-BAG report: `POSTR1-P5-SYSTEM-UPDATE-INCLUSION/attempts/implementer-1/`.
- Next exact step: `POSTR1-P5-GATE-CLOSURE-V12F` re-runs the live closure against this official image. T3-P remains OPEN/BLOCKING — not marked DONE here.

## 22. Gate-P5 closure re-run V12F (2026-09-15) — RED, Gate P5 OPEN, T3-P OPEN, new shipped defect D5

V12F implementer re-ran the full closure on the orbiter lane at HEAD `5d33920` (D4 `system-update` selection + D3 `profile.id` fix + V12D-carried harness delta integrated). The sysupd image (from `16fdbedd`) was treated as absent (not SHA-bound to this HEAD); clean archive (sha `022718fc…`) delivered with the D4 fix confirmed in the delivered tree. Keys/bundles re-minted through production builders only (fresh ed25519 `greia-release-main`; 64 MiB ext4 base payload with pinned issuer; seq20 `77ab514a…` / seq21 `5896f235…` / seq23 `79468c2d…`, all signature-verified). Official `acer-aspire-one-i386-ab` image rebuilt with `GREIA_AB_*` on the sudo command line: 1320157184 B sha `cfbb2d97…`, payload squashfs `2b1f55d0…`, footprint installed/filesystem-used/accounted 985 < required 1000 PASS (+4 vs the 981 baseline; preferred-≤800 warning retained); USB bundle == minted seq20. D4 verified fixed at every stage (payload + live manifests carry `python3-cryptography 38.0.4-3+deb12u1`; live AND target chroots `import cryptography` 38.0.4 + Ed25519 OK; production `inspect_update_bundle` + `verify_update_signature` inside the built live bytes verifies the real seq20 bundle GREEN); D3/D1/D2 intact in the image (canonical `profile.id`, both socket wants-links, zero `^StandardInput` on socket-activated units).

Closure run (`/tmp/greia-p5-v12f-closure.py`, sha `02de92e0…`, V12C two-phase shape, frozen P5.4 baseline, pinned HEAD): positive control RED-as-expected (`d31_fn=None` → BLOCKED naming the unpinned D31 mapping), then the real install-execute leg timed out after 1200 s (guest boots to login, never powers off) — 0/9 predicates GREEN. Journal-to-console replay on a disposable copy of the run clone isolates new shipped defect D5: the install-transaction service now gets PAST release-signature verification into `finalize` and dies in hardware-support install — `TransactionServiceError: fresh A/B install refused: hardware-support command failed: chroot: cannot change root directory to '/run/greia-slots/slot-a-401': Operation not permitted` (chain: `execute_fresh_ab_install` → `slot_writer.finalize:1159` → `slots:173` → `block_slots:679` → `slots:126` → `hardware_support_install:61` → `device_seams:143`). Cause: the shipped `greia-install-transaction.service` grants only `CAP_SYS_ADMIN` (bounding + ambient, pinned by `tests/test_installer_unit_contract.py:411-414`) while shipped `hardware_support_install.py` runs `chroot <slot> apt-get …` (three invocations) via the production runner — `chroot(2)` requires `CAP_SYS_CHROOT`, so the denial is deterministic capability law, identical on physical Acer hardware. The unit comment's "CAP_SYS_ADMIN and nothing else" evidence covered mount/write only, never chroot; D1/D3/D4 masked this path in sequence, so D5 is new line-of-sight, not a regression. Both the unit file and the implementation choice sit outside this task's Allowed changes, so no repair was attempted and no clone-side bypass (that would be harness substitution).

Procedure note (facility, not product): the closure driver must run as root (`sudo -n python3`, the established V9/V11 procedure) — `tools/x8_qemu/product.py` loop/mount calls carry no sudo prefix and `orb` is not in the `disk` group, so an unprivileged driver run fails pre-QEMU at `inject_live_clone` with `losetup: Permission denied` (recorded; first V12F launch hit exactly this, then relaunched clean as root).

Lane left healthy (own loops detached via `losetup -d`, no stray mounts/processes, never `umount -R`; pre-existing stuck deleted-file loops + key/sudoers for parent/owner). Evidence: T-BAG `POSTR1-P5-GATE-CLOSURE-V12F/attempts/implementer-1/` (report + `v12f-status.json` + `closure.log` + `diag-execute-serial.log`); orbiter-side artifacts remain in `/tmp/greia-p5-v12f-*` + `/tmp/v12f-diag-*`. Next: product authority decides the D5 repair side (grant `CAP_SYS_CHROOT` to the install-transaction unit vs remove `chroot` from the hardware-support install path; the contract test pins the current set and must move with the decision), then official rebuild + closure re-run. T3-P remains OPEN/BLOCKING.

## 23. D5 installer `chroot` privilege repair (2026-09-15) — unit carries `CAP_SYS_CHROOT`, hardware-support install leg proven on disposable loop target (`POSTR1-P5-INSTALLER-CHROOT-PRIVILEGE-FIX`)

Decision (bounded minimum-privilege determination, recorded in commit `2eae3f93`): retain the shipped `chroot` hardware-support install path and add exactly `CAP_SYS_CHROOT` to `CapabilityBoundingSet` + `AmbientCapabilities` (final set `CAP_SYS_ADMIN` + `CAP_SYS_CHROOT`, nothing else). Rationale: `TargetHardwareSupportInstaller.install()` runs `chroot <slot> apt-get update/install/clean` (three argv-array invocations) through the production `SubprocessHardwareSupportRunner` (`shell=False`) on the A/B finalize path; `chroot(2)` fails EPERM without `CAP_SYS_CHROOT` (V12F traceback), so the old "nothing else" comment was evidenced for mounts only, never for `chroot`. The remove-`chroot` alternative would fork install plumbing with a second writer/finalizer and no minimality proof, so it is rejected. Envelope unchanged: `ProtectSystem=strict`, `NoNewPrivileges=yes`, `AF_UNIX`-only, the six `ReadWritePaths`, single writer/finalizer. Contract test renamed to `test_capabilities_are_exactly_cap_sys_admin_and_cap_sys_chroot` plus a `chroot`-leg regression (declared capability + three `chroot` argv arrays + `shell=False`); local positive control (withdraw `CAP_SYS_CHROOT` → 2 RED, restore → 19/19 GREEN).

Orbiter proof from HEAD `2eae3f93` (clean archive sha `7d0ab8ff…`, keys/bundles re-minted through production builders: seq20 `0a969941…` / seq21 `ab6d1c26…` / seq23 `6ec20b88…`, all signature-verified): official `acer-aspire-one-i386-ab` image rebuilt with `GREIA_AB_*` on the sudo command line — 1320157184 B sha `f2aedcfe…`, payload squashfs `269ce745…`, USB bundle == minted seq20, footprint installed/filesystem-used/accounted 985 < required 1000 PASS (unit-declaration change, no new package; preferred-≤800 warning retained); live manifest keeps `python3-cryptography 38.0.4-3+deb12u1` (D4 intact). Built-artifact proof (read-only USB + squashfs mounts, single unmounts): the live installer unit declares exactly `CAP_SYS_ADMIN CAP_SYS_CHROOT` with the rest of the envelope intact, and the live code keeps the three `chroot` legs.

Product-path proof on a disposable 1 GiB ext4 loop target (single usr overlay off the built live root, usrmerge symlinks, apt-bind, proc/sys/dev/devpts; real medium pool verified: 58 packages; real built `TargetHardwareSupportInstaller.install` + production runner under `systemd-run` with the exact unit sandbox): old caps reproduce the V12F EPERM byte-identical (`chroot: cannot change root directory … Operation not permitted`, exit 10); repaired caps complete the leg (`INSTALL_OK: ['firmware-ast']`, update/install/clean all RC 0; `dpkg -l` → `ii`; firmware file on the slot layer). Bare-`chroot` sensitivity: old exit 125 EPERM / new exit 0. One harness-only detour is honestly recorded (first positive attempt failed at dpkg unpack for a non-usrmerged hand-built target + stacked duplicate overlay mounts; target rebuilt clean, identical real install re-ran GREEN — no source/privilege change to force green). Lane left clean (single unmounts only, both own loops detached, never `umount -R`; key/sudoers + pre-existing loops for parent/owner). Evidence: T-BAG `POSTR1-P5-INSTALLER-CHROOT-PRIVILEGE-FIX/attempts/implementer-1/` (`d5-status.json` + `proof-excerpts.txt`); orbiter-side artifacts in `/tmp/greia-p5-d5-*` + `/tmp/greia-p5-out-d5/`. Next: `POSTR1-P5-GATE-CLOSURE-V12G` re-runs the full live closure against this image. T3-P remains OPEN/BLOCKING — not marked DONE here.

## 24. Installer no-network/tool guard scoped to systemd directives (2026-09-15) — test-only (`POSTR1-P5-INSTALLER-SVC-TEST-SCOPE`)

Test-only change to `tests/test_installer_hardware_support_service.py` (no shipped unit, no `src/`): local `_directive_text` helper keeps only systemd directive lines (drops blanks and lines whose first non-whitespace char is `#` or `;`); both negative guards (`apt-get`/`curl`/`wget` absence on both units; `GREIA_HARDWARE_SUPPORT_POOL` absence on the UI unit) now evaluate directive text, and all other assertions are unchanged. New `test_directive_scope_positive_control` proves both directions on synthetic text (comment-only tool mention → no hit; real `ExecStart` naming `curl` → hit); sensitivity re-proven in-memory against the shipped units (comment-injected prose trips the old whole-file scan but not the directive scan; both shipped units carry 0 guarded tokens in directives today). Evidence: full local suite 3388 OK (skipped=3) — prior baseline 3387 OK + 1 new test, no new failure; `git diff` touches only the test file. T3-P remains OPEN/BLOCKING — not marked DONE here.

## 25. Gate-P5 closure re-run V12G (2026-09-15) — RED, Gate P5 OPEN, T3-P OPEN, D5 proven effective on the product path, new shipped defect D6 (slot payload has no `apt-get`)

V12G implementer re-ran the full closure on the orbiter lane at HEAD `98b06079` (D5 `CAP_SYS_CHROOT` repair + D4 `system-update` selection + D3 `profile.id` fix + test-scope §24 integrated; tree `7657e5cb`). Prior V12G residue (image built from the tree-identical checkpoint `6cf3fef1`) was treated as ABSENT (not SHA-bound to this HEAD); clean archive of HEAD (tgz sha `bd8dc86d…`, match both sides) delivered to `/tmp/greia-p5-v12g5-src` with D5 caps + D4 selection confirmed in the delivered tree. Keys/bundles re-minted through production builders only (fresh ed25519 `greia-release-main`; 64 MiB ext4 base payload with pinned issuer; seq20 `c66d46bc…` / seq21 `5e2d611d…` / seq23 `1526ce11…`, all signature-verified). Official `acer-aspire-one-i386-ab` image rebuilt with `GREIA_AB_*` on the sudo command line: 1320157184 B sha `3d3a01de…`, USB bundle == minted seq20, footprint installed/filesystem-used/accounted 985 < required 1000 PASS (preferred-≤800 warning retained). Built-artifact proof (read-only loop + unsquashfs, single unmounts): target `profile.id` canonical; live AND target manifests carry `python3-cryptography 38.0.4-3+deb12u1` (D4 intact at both levels); the built live installer unit declares exactly `CAP_SYS_ADMIN CAP_SYS_CHROOT` (D5 reached the artifact); target payload enables `greia-system-update.socket` via `sockets.target.wants`. Focused local suites 92/92 GREEN during the build window.

Closure run (`/tmp/greia-p5-v12g5-closure.py`, sha `c4d9cd07…`, V12F two-phase shape, frozen P5.4 baseline, pinned HEAD, run as root per the V9/V11 procedure): positive control RED-as-expected (`d31_fn=None` → BLOCKED naming the unpinned D31 mapping), then the real install-execute leg timed out after 1200 s (guest boots to login, never powers off) — 0/9 predicates GREEN, P5.4 record NOT_READY, D31 seed unexecuted, T3-P left OPEN. Journal-to-console replay on a disposable copy of the run clone (only added `systemd.log_target=console` + `journald.forward_to_console` on the one grub.cfg linux line; run clone read-only source) shows the IDENTICAL call chain as V12F (`slot_writer.finalize:1159` → `slots:173` → `block_slots:679` → `slots:126` → `hardware_support_install:61` → `device_seams:143`) diverging only at the final errno: `TransactionServiceError: fresh A/B install refused: hardware-support command failed: chroot: failed to run command 'apt-get': No such file or directory` (was V12F `chroot: cannot change root directory … Operation not permitted`). D5 is therefore proven effective on the product path (`chroot(2)` EPERM gone), but the install-execute leg does NOT pass the hardware-support leg — acceptance bullet 2 red.

New shipped defect D6, forensically closed (read-only loop mount of slot A on the quiescent disposable target): slot A holds ONLY `{etc, lost+found, run, var}` — the raw streamed 64 MiB minted bundle payload — with no `/usr`, no `/bin`, no `apt-get`. `fresh_ab_install` streams `open_bundle_payload_stream(bundle)` verbatim into the slot and `finalize` then `chroot <slot> apt-get update/install/clean`, so with any bundle built by the V12E/V12F/V12G mint procedure the ENOENT is deterministic: nothing in the slot can execute `apt-get`. No in-guest log, manifest, or earlier predicate masked this — V12F died one stage earlier (EPERM), so D6 is new line-of-sight, not a regression. Resolution needs product/architecture authority outside the closure lane's Allowed changes (`src/greia_installer`, `src/greia_platform`, `tools/greia_update.py`, `build/*` all excluded): either release payloads must be full Debian systems carrying apt/dpkg (and the mint must build one — a methodology change with footprint/capacity consequences for the 1 GiB slot), or the install flow must stop assuming `apt-get` inside a payload-only slot. No fixture hack was applied to force green (same principle as the D5 task's refused harness substitution).

Lane left healthy (own loops detached — build-forensics loop43 and diag loop — no stray mounts/processes; diag QEMU SIGTERM'd by the operator only AFTER the decisive traceback was captured at 17:45, so its "QEMU EXITED" line is a driver logging imprecision, not a guest power-off; pre-existing loops + key/sudoers for parent/owner). Evidence: T-BAG `POSTR1-P5-GATE-CLOSURE-V12G/attempts/implementer-5/` (report + `v12g5-status.json` + `closure.log` + `diag-execute-serial.log`); orbiter-side artifacts in `/tmp/greia-p5-v12g5-*` + `/tmp/greia-p5-out-v12g5/` + `/tmp/v12g5-diag-*`. Next: product authority decides the D6 repair side and issues the rebuild + closure re-run successor; do NOT mark T3-P DONE. T3-P remains OPEN/BLOCKING.

## 26. Session 02 source-scope closure (2026-09-16) — composer roles, real ext4 slot, shared validator; D6 resolved at SOURCE level

Current installed phase: Session 02 of `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md` is complete for source scope (T01–T04 all reviewer-accepted PASS). Current route: the Session 02 boundary build-host artifact leg, then Session 03 (owner release CLI + compact release outputs).

What was implemented (source scope, all SOURCE-level evidence):

```text
T01: build/lib/compose.sh role-typed compose_root (target|live-installer); build/build-image.sh thin target consumer
T02: build/build-installer-image.sh through the same engine with the live-installer role; engine + target consumer byte-unchanged
T03: shared slot completeness validator in src/greia_platform/slot_writer.py, fail-closed in SlotFinalizer.finalize before any install/build/write
T04: tools/build_release.py real-ext4 producer (mkfs.ext4 -d -> e2fsck -> resize2fs -M -> e2fsck -> zstd -19, T03 validator before image bytes, debugfs verifier, unsigned v3 bundle round-trip)
```

D6 status: RESOLVED at SOURCE level. The §25 defect (slot payload with no `apt-get`) is closed by the Session 02 repair side the §25 evidence demanded: release payloads are now complete target-root ext4 images carrying `apt-get`/`dpkg`/`env`, produced from the composed target root and refused as skeletons by the shared validator before compression and before slot finalization. D6 is not a live defect anymore; what remains is the build-host artifact proof, not a product decision.

Evidence boundary (honest): SOURCE-level only. Contract suites green (`test_build_release` 8/8, `test_slot_writer` 45, `test_system_update*` 51, `test_update_v3_bundle` 6, `test_build_*` 45, plus T01/T02 shell-contract/boot suites) with negative/positive/sensitivity probes; real zstd/v3-bundle bytes exercised. No privileged debootstrap/chroot/loop build ran here and no real image or bundle artifact was produced — e2fsprogs behavior was proven through the injected runner seam. This evidence does not certify VM/image or physical-hardware behavior.

Skill/manual disposition: `skills/greia-os-work/SKILL.md` and `docs/agents/GREIA_AGENT_OPERATIONS.md` required no change for Session 02 — the skill already routes lifecycle work to the 2026-09-15 plan and marks the signed v2 flow historical, and the manual's build/update procedure (before-debootstrap apt-cache mounts, capable build-host process rules) is untouched by the composer/slot work.

Next exact step: run one privileged Linux build-host `build-payload` → `verify-payload` → bundle cycle to promote SOURCE-level proof to a real-artifact run (the `mkfs.ext4` size-suffix spelling is pinned by the seam test and confirmed by that run); then Session 03. Do not treat shipped product composition (T3-P) as complete until the lifecycle plan's closure criteria say so.

## 27. T07 documentation correction to ADR 0036 lifecycle reality (2026-09-16)

Docs-only correction of the four residual inconsistencies flagged outside T05's write boundary (T05 reviewer-1 follow-ups). No implementation change; no `src/`, `build/`, `tools/`, `tests/` or Activity file touched.

- `docs/development/README.md` index bullets now describe the unsigned v3 flow, consistent with the rewritten workflow runbook.
- Gate E in `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md` no longer requires trusted public-key provisioning, signing-key custody/rotation/revocation, or exact signature verification; stale "signed" intro wording fixed and the "bad signature" failure probe restated as corrupt/tampered bundle.
- `skills/greia-os-work/SKILL.md` routes lifecycle work to Session 02 source-complete with the build-host artifact boundary leg as the current entry point, then Session 03 (routing only).
- `docs/product/SYSTEM_UPDATES.md` states the Parent client never decides release trust (v3 has no signature).
- Progress recorded append-only in the 2026-09-15 plan ledger; no earlier plan content modified.

Current route unchanged: Session 02 source-complete for source scope, build-host artifact leg next, then Session 03 (see §26).

## 28. T09 documentation conformance to unsigned v3 outside Gate E (2026-09-16)

Docs-only amendment completing the ADR 0036 pass T07 scoped to Gate E. No implementation change; no `src/`, `build/`, `tools/`, `tests/` or Activity file touched.

- `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`: reconciled gaps item 5, Gate B release property, 7.1 artifacts, Gate K review, Gate O build record, RC evidence pack, release-track publish step, and section 27 items 7/17 to unsigned `.greiaupdate` v3 reality (no Greia release signing key, no manifest/signature verification, no custody/rotation/revocation, no cryptographic anti-rollback). Legitimate non-release-signature content preserved.
- `docs/product/SYSTEM_UPDATES.md`: pre-write step now names machine/profile/board compatibility and PERSIST schema readability re-checks, with no signature/trust implication.
- Progress recorded append-only in the 2026-09-15 plan ledger; no earlier plan content modified.

Current route unchanged: Session 02 source-complete for source scope, build-host artifact leg next, then Session 03 (see sections 26-27).

## 29. R2 Session 02 COMPLETE — real-artifact leg proven on orbiter (2026-09-16)

T-BAG run R2 finished `COMPLETED`: s01 Gate PASS, s02 Gate PASS
(`TBag/runs/R2/plan/PHASE-s02-GATE-01.md`, auditor independently
reproduced every exit predicate plus `make verify`). T-BAG run state
itself is git-ignored and stays local; this section is the durable
project record.

- **T11 (integrated):** production payload producer
  (`tools/build_release.py`) now completes a ~1 GiB Acer-class
  `zstd -19` step inside stated, configurable, observable bounds
  (600 s commands / 1800 s compression via the runner seam),
  `zstd -19` output spelling unchanged, ext4/no-signing/`ZIP_STORED`
  contract intact.
- **T13 (integrated):** hardware-support producer
  (`build_hardware_support_set`) fails closed under the same timeout
  contract (no raw `TimeoutExpired` leak, non-positive bounds refused).
- **T15 (PASS, accepted):** Session 02 boundary verified with the real
  artifact leg on the owner-provisioned orbiter lane
  (`orb@192.168.68.113`): real `acer-aspire-one-i386-ab` target root
  composed through the production engine, real ext4 `payload.ext4.zst`
  via the real runner path, `verify-payload` green, v3 bundle
  round-trip holds. All source-level predicates re-measured at the
  pinned HEAD, nothing carried on trust.
- Superseded without execution: T06/T08/T10 (local-container
  attempts killed by Docker Desktop RAM pressure/daemon stall) and
  T12/T14 (re-briefs of the same). No predicate was weakened at any
  replan step; red results stayed red until proven.
- Evidence boundary: SOURCE + REAL-ARTIFACT (orbiter lane).
  `make verify` green at the boundary (3415 tests OK, 3 skipped).
  This does not certify VM/physical-hardware behavior.

Standing constraints from this run (owner-ordered, recorded in
`TBag/runs/R2/authority/owner-decisions/`, local-only):

- Local-container legs: one container at a time, `--memory=4g --rm`,
  pre-flight daemon/RAM/disk check with fail-closed BLOCKED, post-leg
  removal of everything created, never touch foreign containers,
  never host-wide prune.
- Orbiter lane: read-only access check first, clean-archive delivery,
  single unmounts only, never `umount -R` a chroot with host bind
  mounts, `/dev`+`/proc`+`/sys` verified before and after.
- T-BAG never launches/quits Docker Desktop itself; only `docker` CLI
  against the running daemon.

Current route: Session 02 DONE. Next is Session 03 (owner release CLI
+ compact release outputs) per the 2026-09-15 plan.

## 2026-09-18 — R2 repair: worker lanes exhausted, owner hardware legs pending

> HISTORICAL — NOT CURRENT ROUTING. The "owner hardware legs pending" path
> below was parked and then cancelled by explicit owner decision the same day
> (see "R2 run paused" and "R2 RETIRED" below); the "Three owner-operated
> executions owed" are not owed for R4. Retained as history only — §30 owns
> current R4 routing and requires no owner hardware run.

T-BAG R2 `repair` (analyst + grunt pinned to
`opencode / opencode-go/muse-spark-1.3-contributor`; launches serialized —
parallel workers collide on the shared 6.9 GB opencode.db). Integrated with
reviewer PASS: source tranche T01–T18, HW-01A Orbiter payload leg (headroom
1196425216 ≤ 1610612736 GREEN at `4c571995`), HW-01B (STOP), HW-05 comment
reword, HW-03A (STOP), HW-03B (NOT-EXECUTABLE). Recorded BLOCKED (red
preserved): HW-02 (NOT-EXECUTABLE, proof carried by HW-03), HW-03 (needs
owner hardware). Queued: HW-04 §24 close. Gate GATE-04 BLOCKED; Session 03
closed until §23 physical predicates go green.

Precise status + owner runbook: `HW-03-PHYSICAL-LEGS.md` (repo root). Three
owner-operated executions owed, in order: (1) disposable-Linux installer
build from `4c571995` reusing the HW-01A bundle, (2) QEMU exact-service
staging with logs, (3) Acer §18 acceptance. Orbiter lane: key-only ssh
provisioned (`orb@192.168.68.113`); password nowhere stored. No further
worker attempts until the §24 evidence block returns; HW-02 deliberately
held (re-running only re-proves NOT-EXECUTABLE).

## 2026-09-18 — R2 run paused by owner

> HISTORICAL — NOT CURRENT ROUTING. This pause was superseded the same day by
> the owner cancellation recorded immediately below; the "resume trigger"
> asking the owner for a §24 evidence block no longer routes anything. R4
> requires no owner hardware run (§30).

Owner stopped the plan. T-BAG R2 status: `paused-by-user` (zero live
workers; HW-02 deliberately held, HW-03 parked awaiting owner hardware per
`HW-03-PHYSICAL-LEGS.md`, HW-04 pending evidence). Gate GATE-04 BLOCKED;
Session 03 closed. Resume trigger: owner returns the §24 evidence block
(installer identity, staging verdict + logs, Acer acceptance) — then HW-04
runs and PHASE-GATE-01 re-audits narrowly.

## 2026-09-18 — R2 RETIRED by owner cancellation (final)

Owner chose "cancel with record". T-BAG R2 is `abandoned`: HW-02/HW-03/HW-04
cancelled without execution per `TBag/runs/R2/owner-decisions/R2-cancellation.md`;
gate BLOCKED and all red predicates preserved as history (no waiver, no
proxy, no successor). Integrated work stands: source tranche, HW-01A Orbiter
GREEN (`4c571995`), HW-01B/HW-03A STOPs, HW-03B NOT-EXECUTABLE, HW-05.
Status/runbook `HW-03-PHYSICAL-LEGS.md` remains the hardware handoff should
evidence ever return under a new run. Lifecycle ledger updated in
`docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`.

## 30. Session 02 R4 autonomous repair — authoritative closeout (2026-09-19)

This section is the single authoritative R4 closeout. It supersedes all
active-looking owner-routing text above (§8b "Session 03 must not begin until
the owner completes them" / "Exact owner next steps", the paused-run "resume
trigger", and the dangling `docs/handovers/TBAG-opencode2-plugin-handoff/`
references — that directory is deleted). **No owner hardware work is required
to finish R4.** R4 is an autonomous source-only repair tranche; every
physical/Orbiter predicate below that is not yet proven stays DEFERRED, never
an owner task.

- **R2 hardware owner-run path: HISTORICAL / CANCELLED.** Owner chose "cancel
  with record" (T-BAG R2 `abandoned`); HW-02/HW-03/HW-04 closed without
  execution, gate BLOCKED preserved as history. `HW-03-PHYSICAL-LEGS.md`
  remains a historical handoff outside the R4 write boundary, not a current
  instruction.
- **R3 landed, but review found R4 defects.** At the R4 baseline the
  executable source still carried: (A) `LegacyBiosAbAdapter.BOOT_CONTROL_BYTES
  = 32 * MIB` against the binding A21 64 MiB contract
  (`src/greia_installer/layout.py`); (B) Acer `image.size_mib = 4352`
  inflated by installed-disk capacity via `BuildProfile`
  duplicate-overhead validation (`tools/build_profile.py`,
  `build/profiles/acer-aspire-one-i386-ab.toml`); (C)
  `refuse_unless_persist_fits` double-counting the resident bundle against
  PERSIST free space (`src/greia_platform/candidate_support.py`); (D) split
  build/runtime hardware-support parsers with divergent verdicts and no
  shared module; (EF) whole-artifact buffering plus two-pass candidate
  staging; (G) operator-typed `--payload-uncompressed-bytes` trusted without
  artifact verification (`tools/greia_update.py build`). Repair ownership:
  sibling R4 code lanes R4-A-BOOT / R4-B-CAPACITY / R4-C-PERSIST /
  R4-D-PARSER / R4-EF-STAGE / R4-G-RECEIPT; integration acceptance belongs to
  R4-V-VERIFY at the final integrated HEAD, not to this docs tranche.
- **R4 final SHA (docs tranche):** base `c58051c2` with an uncommitted
  docs-only delta at report time (`HANDOVER.md`,
  `docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md`,
  `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`;
  `git diff --check` clean). The final integrated SHA is owned by
  lane integration + R4-V-VERIFY, which re-binds all evidence to it.
- **Focused test results (this tranche, autonomous):** 129 tests OK,
  1 skipped, across `test_acer_ab_slot_capacity` (6),
  `test_release_cli_finalized_capacity` (11), `test_candidate_support` (19),
  `test_system_update_service_orchestration` (7, 1 skipped),
  `test_build_profiles` (9), `test_build_release` (20), `test_slot_writer`
  (45), `test_system_updates` (12); `git diff --check` clean;
  `make shell-check` clean. Full `make verify` exceeds this lane's execution
  budget (full-suite discovery >300 s); complete-gate verification is owned
  by R4-V-VERIFY at the integrated HEAD.
- **Orbiter evidence:** earlier real-artifact proofs stand and are NOT
  re-claimed at this SHA — R2 T15 Session 02 boundary (orbiter lane,
  `make verify` 3415 OK / 3 skipped) and HW-01A payload leg at `4c571995`
  (383798895 B compressed / 1111490560 B uncompressed, headroom 1196425216
  ≤ 1610612736 GREEN). **R4-bound Orbiter reproof at the current SHA is
  PENDING** (no Orbiter run from this docs worktree; autonomous-only lane:
  no mounts, no loop devices, no installs).
- **Deferred physical acceptance:** installer disk assembly, exact-service
  staging against a real inactive target, Acer fresh-install / update /
  rollback / PERSIST-survival acceptance, and Pi/UEFI hardware legs remain
  UNPROVEN and DEFERRED — listed here, not executed, never waived.
- **Session 03 status:** CLOSED until the R4 code lanes integrate and
  R4-V-VERIFY accepts the final HEAD; opening it is a lifecycle-plan
  decision, never an owner hardware errand arising from R4.

Cross-references: lifecycle ledger entry in
`docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`
(2026-09-19 R4 docs closeout); payload/bundle procedure in
`docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md` (R4-bound
reproof wording).

## 31. R4 SHA-bound closeout — final integrated HEAD `c4ab45aa` (2026-09-19)

Append-only closeout bound by R4-V-VERIFY5 to the final integrated HEAD.
§30 above is preserved as the docs-tranche record (base `c58051c2` + delta,
full verify and Orbiter reproof PENDING at that point); this section, not
§30, carries the final SHA binding. Existing `HISTORICAL — NOT CURRENT
ROUTING` banners above are kept as-is. No owner hardware errand is added
by this entry; every unproven physical predicate below stays DEFERRED.

- **Final integrated SHA:** `c4ab45aaea5968d5a1bf911e2b883b012dd8cc3e`
  (`git rev-parse HEAD`; `git status --short` empty before and after all
  runs; `git diff --check` exit 0; `git log --oneline -3` →
  `c4ab45aa` checkpoint / `bf192072` baseline / `23c76572` debris removal).
- **Focused-suite results (all OK at that SHA, `PYTHONPATH=src python3 -m
  unittest discover -s tests -p <file>`):** `test_acer_ab_slot_capacity` 6;
  `test_release_cli_finalized_capacity` 11; `test_candidate_support` 19;
  `test_system_update_service_orchestration` 7 (1 skipped —
  systemd-analyze absent); `test_build_profiles` 9; `test_build_release`
  20; `test_slot_writer` 45; `test_system_updates` 12;
  `test_payload_receipt_binding` 17; `test_hardware_support_archive_verdicts`
  22; `test_candidate_support_streaming` 15; `test_candidate_support_persist`
  5; `test_support_outer_bound` 7; `test_installer_layout` 15;
  `test_installer_legacy_ab_layout` 16; `test_legacy_boot_control_contract`
  3; `test_ab_capacity_separation` 6; `test_build_profiles_storage` 11;
  `test_persistent_layout` 40; `test_hardware_support_pool_build_script` 3;
  `test_hardware_support_pool_finalize` 7;
  `test_hardware_support_pool_manifest` 6;
  `test_hardware_support_installed_size` 3;
  `test_installer_hardware_support_install` 3;
  `test_installer_hardware_support_pool` 13;
  `test_installer_hardware_support_service` 3;
  `test_installer_builder_hardware_support` 4;
  `test_acer_ab_release_identity` 5; `test_greia_update_tool` 4;
  `test_update_v3_bundle` 6; `test_system_update_service` 35;
  `test_system_update_streaming` 4; `test_clone_neutral_target` 6;
  `test_installer_persist` 20; `test_release_v2` 13. Named legs confirmed
  by test name: explicit typed-without-receipt refusal,
  explicit missing-sizes refusal, explicit+seam success, explicit
  correct-receipt build, explicit 5-way mismatch refusal, single-schema-owner
  pin, strengthened full-bundle compressed-overflow leg, single-production-bound
  assertion, shared+runtime `read(-1)` refusal, single-open-per-member,
  outer-bound round-trip/mismatch/pre-stream, order-lift both directions.
- **`make verify` result:** `make validate` exit 0; `make shell-check`
  exit 0 (no output); `make footprint` exit 0; `make test` → Ran 3587,
  FAILED errors=11 skipped=4. The 11 errors are preserved red, pre-existing
  and environmental: all `OSError: AF_UNIX path too long` at
  `tools/x8_qemu/lifecycle.py:926 listener.bind(socket_path)` (1 in
  `test_boot_health_product_composition`, 2 in `test_t3_update_production`,
  8 in `test_x8_qemu.*`; mandated TMPDIR alone 125 chars, typical child
  socket path 149 chars vs the 104-char darwin `sun_path` limit). All 11
  failing files sit outside the R4 delta surface; identical signature to
  accepted R4-V-VERIFY4 (3587/11/4). The 4 skips are preserved
  environmental: 'no category targets at root view', 'no category targets',
  'no sfdisk/blkid on this host', systemd-analyze-absent skip. Not re-run
  under a shorter TMPDIR: the scratch boundary is launcher-mandated.
- **Orbiter §§11.1–11.8 (same SHA):** §11.1 identity PROVEN (above). §11.2
  unit legs + `make verify` stages PROVEN (above). §11.5 CLI-level positive
  bundle PROVEN (real CLI `tools/greia_update.py build`,
  `--profile-file build/profiles/acer-aspire-one-i386-ab.toml`, synthetic
  64 KiB zstd payload + producer-measured receipt, synthetic 2-package pool
  via production `build_hardware_support_set`): rc 0, bundle 1753 B,
  manifest schema 3, profile `acer-aspire-one-i386-ab`, release
  `greia-0.14.0`, payload compressed 282 / uncompressed 65536 / minimum
  65536 (sha `5b6f4784…`), support compressed 750 / extracted bound 88576
  (sha `c66418ea…`); slot capacity 1610612736 (1536 MiB), payload base
  65536, payload minimum 65536, support installed 65536, finalization growth
  67108864, metadata reserve 16777216, required total 84017152, remaining
  headroom 1526595584. §11.6 CLI-level over-capacity refusal PROVEN (same
  path, per-package installed 900 MiB → support installed 1887436800):
  rc 2, stderr `required=1971388416 exceeds slot capacity 1610612736`,
  output file absent. §11.7 PERSIST sensitivity incl. pre-stream outer-bound
  leg PROVEN. §11.8 single-traversal/single-extraction/cleanup
  instrumentation PROVEN (1 traversal / 1 extraction per stage, 2 payload
  writes, 0 compressed tmp files, shared pool identity, cleanup after
  success+failure via `test_candidate_support_streaming` 15/15 +
  `test_support_outer_bound` 7/7). Preserved reds (never waived): strict
  artifact legs needing a Linux build host — real target-root compose via
  debootstrap, real relocatable ext4 payload via mkfs.ext4, real dpkg-built
  `.deb` pool, `systemd-analyze verify`, mounts/loop — are UNPROVEN on the
  darwin host (`which debootstrap mkfs.ext4 dpkg-deb systemd-analyze` all
  absent) and stay DEFERRED; `test_clone_neutral_target` 6/6 stands as unit
  proxy only.
- **Deferred-physical list (per §12):** no Greia install, repartition,
  mounts/loop mounts, destructive block tests, Docker, QEMU-physical runs,
  or Acer hardware work executed. Deferred, required before binary/family
  release but not before R4 source closure: Acer fresh install; real
  installed A/B partition write; real service under exact systemd capability
  sandbox using `chroot apt-get`; candidate boot; health commit; rollback
  after failed boot; PERSIST survival across real install/update; physical
  USB installer boot; 4161 MiB device-boundary reproof on hardware;
  hardware-measured footprint/timing.
- **Session 03 status:** CLOSED under the lifecycle plan's sequencing until
  the lifecycle plan opens it; opening Session 03 is a lifecycle-plan
  decision, never an owner hardware errand arising from R4. R4 source
  closure is bound here; the owner/Linux lane owns any deferred-physical
  Orbiter legs.

Cross-reference: lifecycle ledger R4 closeout entry in
`docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`
(2026-09-19, final SHA `c4ab45aa`); verification evidence in
R4-V-VERIFY5 (`make-test.log`, `make-validate.log`, `make-shellcheck.log`,
`make-footprint.log`, `scratch/orbiter-cli/`).

## 32. R4 Linux-lane closeout — R4-V-LINUX verification-8 at `762d4ebd` (2026-09-19)

Append-only rebinding of gaps G1–G3 after Linux proof. §§30–31 above are
preserved as the docs-tranche (`c58051c2` + delta) and darwin-bound
(`c4ab45aa`, carried numbers, strict legs UNPROVEN) records; this section,
not §30/§31, carries the Linux-bound numbers. No earlier section is
rewritten. No owner hardware errand is added by this entry; every unproven
predicate below stays DEFERRED or preserved red, never waived.

- **Linux-proven SHA:** `762d4ebdfa11d2f0c560cc990c68ecef3985bb14`
  (R4-V-LINUX verification-8; `git bundle` of the assigned view cloned on
  Orbiter → `git rev-parse HEAD` exact match, `git status --short` clean,
  `git diff --check` exit 0 both sides; zero project writes —
  `Allowed source changes: NONE` honored). Source-tree equivalence:
  `git diff c4ab45aa..762d4ebd` touches only `HANDOVER.md` (§31) and the
  lifecycle ledger (R4-H-DOCS2 entry) — no `src/`/`build/`/`tools/`/`tests/`
  delta — so the Linux numbers below apply to the `c4ab45aa` source content.
- **Focused-suite results (Orbiter, short remote TMPDIR `/tmp/gv8/tmp`,
  never the 123-char launcher scratch):** §10 focused 129/129 OK; extra
  layout/support/persist/receipt/bound coverage 127/127 OK; emoji re-run
  38/38 OK (after host-level `python3-regex` install); PERSIST/streaming/
  outer-bound 27/27 OK; `make validate` exit 0; full `make shell-check`
  exit 0; `make footprint` exit 0.
- **`make verify` result (Orbiter, full `make test`):** Ran 3557 in 2049 s,
  FAILED failures=2 errors=11 skipped=8 (`make verify` stopped at the test
  stage; validate/shell-check/footprint were run separately, all PASS).
  Eight of the 11 errors are a host-prerequisite gap (missing `regex`
  backend), resolved green at host level (`apt-get install python3-zstandard
  python3-regex`, non-destructive) with the 38/38 emoji re-run. The
  remaining 5 reds (2 failures + 3 errors) are preserved red with
  host-divergence mechanisms, each reproduced in isolation (5-test rerun,
  same 2F+3E) and each outside the R4 delta (`git log 23c76572..HEAD`
  touches none of the 5 test files or their production owners):
  forged-peer socket RST on Linux vs clean close on darwin; the
  `/nonexistent-probe` assumption vs qemu-present Orbiter; the
  `_host_which` PATH fallback finding Orbiter `losetup` vs absent on
  darwin; MBR part-UUID `sfdisk` rc 1 (SKIPPED on darwin); the
  qemu-presence assumption in the boot-perf blocked-host test. Denominator
  3557 vs the darwin 3587 is host-conditional collection, not a waived
  comparison. Not re-run under another TMPDIR: the short remote TMPDIR was
  already used throughout.
- **Orbiter §§11.1–11.8 (same SHA `762d4ebd`):** §11.1 identity PROVEN
  (above). §11.2 `systemd-analyze verify` on both service units exit 0
  PROVEN (one informational note: install-transaction.socket special-user
  `nobody` warning, systemd 255); `make verify` stages per the reds above.
  §11.3 real Acer target-root compose via debootstrap RED (preserved):
  `compose_root --role target` requires root debootstrap/chroot/mounts and
  the brief prohibits mounts/loop/install/destructive work;
  `compose_resolve_profile acer-aspire-one-i386-ab target` succeeds; the
  §16 target-root numbers below come from the minimal clone-neutral staging
  used for the real-payload leg (apparent 207 B, allocated 77824 B;
  clone-neutrality proven: etc/machine-id exists+empty, no
  var/lib/dbus/machine-id, no var/lib/systemd/random-seed, etc/ssh empty)
  — labeled minimal staging, not a real debootstrap root. §11.4 real
  relocatable ext4 payload PROVEN (production `build-payload` +
  `verify-payload`, real mkfs.ext4 path): compressed 1668 B, uncompressed
  8646656 B, minimum 67108864 B, profile `acer-aspire-one-i386-ab`,
  release `greia-strict-v8`, sha `979cff63…`, `checked_paths: 13`, both
  exit 0. §11.5 positive support-carrying bundle PROVEN (real dpkg-built
  `.deb` pool `greia-strict-leg 1.0`, Installed-Size 16 KiB via
  `dpkg-deb -f`; production `build-hardware-support` + `greia_update.py
  build` with real profile/receipt facts): support compressed 1508 B /
  extracted bound 83968 / sha `aa7df2bc…`; bundle 3911 B rc 0, schema 3,
  inspect OK; required finalized slot 151011328 B (= 67108864 minimum +
  16384 support installed + 67108864 growth + 16777216 reserve), headroom
  1459601408 B under the 1610612736 B (1536 MiB) slot. §11.6 negative
  over-capacity refusal PROVEN (same path, Installed-Size 1600000 KiB →
  support installed 1638400000): rc 2,
  `required=1789394944 exceeds slot capacity 1610612736`, output file
  absent — REFUSED before publication. §11.7 PERSIST sensitivity incl.
  pre-stream outer-bound leg PROVEN. §11.8
  single-traversal/single-extraction/cleanup instrumentation PROVEN (1
  traversal / 1 extraction per stage, zero compressed tmp files, shared
  pool identity, cleanup after success+failure).
- **Gap rebinding (G1–G3):** G1 (strict Orbiter legs) — substantially
  PROVEN except full-debootstrap target-root compose, which stays RED per
  the no-mount boundary above. G2 (`make verify` green) — NOT green; 5
  host-divergence reds preserved with mechanism (never waived); fixing them
  means changing host-sensitive tests or close semantics, owned by
  implementation follow-ups outside the verification mandate. G3
  (SHA-bound closeout) — bound here, append-only.
- **Worktree-divergence note:** this closeout was authored from the
  R4-H-FINAL worktree (baseline `b7854246`), which carries a 7-file delta
  vs the Linux-proven tree (`tests/test_candidate_support.py`,
  `tests/test_mbr_observed_identity.py`,
  `tests/test_system_update_service.py`,
  `tests/test_update_activation_contract.py`,
  `tests/test_x8_qemu/test_product_boot_perf.py`,
  `tools/x8_qemu/preintro_timing.py`, `tools/x8_qemu/product.py` — exactly
  the host-divergence surface the Linux lane routed to implementation).
  That delta is not covered by the Linux run, is UNPROVEN on Linux, and is
  not claimed here; it is owned by the follow-up triage lanes.
- **Deferred-physical list (per §12):** no mounts/loop, no install, no
  destructive work executed on either lane. Deferred, required before
  binary/family release but not before R4 source closure: Acer fresh
  install; real installed A/B partition write; real service under exact
  systemd capability sandbox using `chroot apt-get`; candidate boot;
  health commit; rollback after failed boot; PERSIST survival across real
  install/update; physical USB installer boot; 4161 MiB device-boundary
  reproof on hardware; hardware-measured footprint/timing.
- **Session 03 status:** CLOSED under the lifecycle plan's sequencing until
  the lifecycle plan opens it; opening Session 03 is a lifecycle-plan
  decision, never an owner hardware errand arising from R4. The gate
  re-evaluates against the Linux-bound evidence above.

Cross-reference: lifecycle ledger R4 Linux-lane closeout entry in
`docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`
(2026-09-19, Linux-proven SHA `762d4ebd`); verification evidence in
R4-V-LINUX verification-8 (report + `/tmp/gv8/logs/make_verify.log`;
short-TMPDIR `/tmp/gv8/*` retained on Orbiter).

## 33. R4 post-review closure patch — local validation pending (2026-09-20)

This entry supersedes §32 for **current routing** while preserving §30–§32 as
historical evidence. It records the small closure patch made after the
independent review of `67c7c445f4be6b7173070ddf1cdace4e434b04bd`.
No hardware or owner-operated acceptance is part of this patch.

### Source corrections landed

- `4f5d4ae9` — `build_update_bundle()` now fails closed when a supplied
  `hardware-support.tar.zst` fails the canonical shared parser. Production no
  longer publishes a bundle that the device is guaranteed to reject merely to
  accommodate synthetic malformed test fixtures.
- `5bb58d7b` — `hardware_support_archive.inspect_archive_file()` now requires
  expected compressed size and SHA-256 together or neither; partial expected
  facts are an explicit API error rather than an internal assertion state.
- Support-carrying tests were updated so normal producer tests use valid support
  archives, while malformed parser-parity tests construct a minimal synthetic
  ZIP member directly instead of weakening production:
  `4728ff24`, `d8eb6453`, `0a7336ce`, `98ff6a8d`, `04adb6ed`.

### Routing/documentation corrections landed

- `docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md` no longer presents
  the old 1 GiB / 1 GiB+1 MiB Acer payload values as canonical release facts.
  Low-level filesystem/minimum values are explicitly release-specific until
  Session 03 hides them behind the owner release CLI.
- `HW-03-PHYSICAL-LEGS.md` now begins with
  **HISTORICAL — DO NOT EXECUTE**. The R2 owner-operated hardware route is
  retired evidence, not current instructions.
- Current release routing is: validate this closure patch locally, then begin
  Session 03 if green. Acer/install/update/rollback hardware acceptance remains
  deferred certification evidence before a binary/family release.

### Validation status

**Not yet claimed PASS in this entry.** Fresh execution is intentionally handed
to the local agent through:

`docs/testing/2026-09-20_R4_CLOSURE_LOCAL_VALIDATION.md`

That brief requires syntax/import smoke, eight focused update/support suites,
`git diff --check 67c7c445..HEAD`, full `make verify`, documentation-routing
checks, and a clean tree before/after. It explicitly forbids source edits,
Docker, mounts, Acer work, and owner intervention during the validation run.

If the returned current-HEAD evidence is green, Session 02/R4 source closure is
complete and Session 03 — owner release CLI + compact release outputs — is the
next engineering session. If validation fails, preserve the exact failure and
repair only the demonstrated defect; do not revive the retired R2 hardware
route or invent a new gate hierarchy.

## 34. First closure validation failed cleanly; stale test fixtures repaired (2026-09-20)

The first local source-only closure validation ran at
`749584b9bba6bea330a12f8e6671adc9bb3a0895` with a clean tree and no source
edits. Its result is preserved here because it exposed a real test-contract
migration problem rather than a product regression:

- py_compile: PASS;
- seven of eight original focused suites: PASS;
- `test_candidate_support.py`: 6 errors because runtime-negative tests still
  asked production `build_update_bundle()` to publish deliberately malformed
  hardware support;
- full `make verify`: 3589 tests, 147 errors, 4 skipped. The first isolated
  failure in `test_ab_install_composition.py` reproduced and had the same
  root cause: many historical tests used "zstd magic + arbitrary bytes" as a
  stand-in support archive, which the new fail-closed producer correctly
  refuses;
- `git diff --check 67c7c445..HEAD`: failed only on two blank EOF lines in
  HANDOVER/lifecycle-plan additions;
- documentation-routing checks: PASS;
- working tree remained clean.

### Repair after that evidence

Production fail-closed behavior was **not weakened**.

A shared tests-only fixture module, `tests/support_artifacts.py`, now owns:

1. a genuinely valid small hardware-support archive for tests that only need
   support to be present; and
2. a deliberately unchecked outer-bundle constructor used only by tests whose
   purpose is to feed malformed support into the runtime parser. Production
   code never imports or exposes that helper.

The malformed `test_candidate_support.py` cases now use the test-only outer
constructor, while historical producer fixtures across A/B install, fresh
install, streaming memory, installer identity, persistent-layout, installed
release identity, release-v3 migration, update activation, product negatives,
T3 update production, sequenced update, and x8 QEMU/recovery tests use valid
support archives.

The two EOF whitespace defects were normalized. The current validation brief
was also strengthened to forbid **all installer/image/root/release builds on the
owner machine**: no installer build, no Greia root composition, no debootstrap,
no `greia_release.py build`, no QEMU, no mounts/loops, no media write, no
Docker, no Orbiter, and no physical hardware action. Validation is source/test
execution only.

Current next action: rerun
`docs/testing/2026-09-20_R4_CLOSURE_LOCAL_VALIDATION.md` at the new `main`
HEAD. Do not infer PASS from the first run or from older R4 evidence.

## 35. Second closure validation narrowed remaining fixture drift (2026-09-20)

Local source/test validation at
`76361d724fe16a761695160f5cc42dd9f4557f62` again used a clean tree and made
no source edits. All eight core focused suites were green. Twelve of fourteen
high-fanout regression suites were green.

The remaining failures were three test-contract classes:

1. `test_candidate_support_streaming.test_truncated_member_refuses_and_cleans_up`
   still asked the strict production producer to emit deliberately truncated
   support before testing runtime cleanup.
2. The T3 default-composition and update-activation "no inactive device"
   tests now carried valid support, so staging advanced to host inventory and
   failed there before reaching the predicate those tests claimed to prove.
3. x8 source-scope lifecycle helpers still created zstd-compressed arbitrary
   support bytes; many bootchain/devproof/devrun3 tests share that helper,
   producing the remaining full-suite error cluster.

Repairs keep production unchanged:

- truncated-support runtime rejection now uses the tests-only unchecked outer
  candidate helper;
- the two no-device tests inject only a complete inventory attestation, then
  retain the real production inactive-slot filesystem/device resolver and
  assert its refusal;
- the x8 lifecycle harness now uses the v3 optional-null hardware-support path
  because those lifecycle tests prove A/B staging/boot/rollback, not support
  installation. Support behavior remains covered by the dedicated support
  suites.

The second run also reported the same two documentation EOF whitespace
failures. This entry and the lifecycle ledger are normalized to exactly one
terminal newline after recording the evidence.

Fresh current-HEAD validation remains required. The validation brief now adds
the complete candidate-support-streaming suite and the x8 bootchain/devproof/
devrun3 source-scope suites. It continues to forbid real QEMU runs, installer
or release-image builds, root composition/debootstrap, mounts/loops, media
writes, Docker, Orbiter, and physical hardware work on the owner machine.

## 36. Third closure validation: focused green, two final full-suite defects isolated (2026-09-20)

Validation at `545f7a45175eeff36ee0851b794e41b31a13ce21` had every
declared focused regression green, `git diff --check` green, documentation
routing green, and a clean tree before/after.

Full-suite execution exposed two remaining issues:

1. `test_x8_qemu.test_lifecycle.ShippedLifecycleTests.test_default_construction_without_seams_fails_closed`
   reproducibly failed for the same prerequisite-order reason already fixed in
   the T3/update-activation tests: valid support allowed staging to reach host
   hardware inventory before its intended absent-inactive-device predicate.
2. `test_x8_qemu.test_devproof.ResourceEnvelopeTests.test_preflight_refuses_before_staging_work`
   failed once in a long full-suite run but passed in isolation and in the
   focused devproof suite. Root cause is a real race in the test: it sampled
   mutable free space and then required only `free + 1 KiB`; deletion of an
   unrelated temporary file between the two disk-usage reads could make that
   requirement fit.

Repairs:

- lifecycle default-seams negative now satisfies only the inventory prerequisite
  with a complete synthetic attestation, retaining the shipped production
  inactive-slot filesystem/device resolver and asserting that exact refusal;
- devproof's direct test and `prove_near_full_preflight()` now demand
  `disk.total + 1`, an impossible requirement independent of concurrent
  free-space changes and exactly matching the helper's documented "more than
  the disk holds" predicate;
- validation now includes the full `test_lifecycle.py` suite and captures the
  complete `make verify` output with a >=1200 s allowance. No installer/image/
  root/debootstrap/QEMU/mount/media operation is authorized.

Fresh current-HEAD validation remains required; no PASS is inferred from older
runs.

## 37. R4 closure — GREEN at validated source HEAD (2026-09-20)

Session 02/R4 source closure is complete.

The local agent validated exact source/test HEAD:

`44927e37dcb150d9fb6cbad7226a52c35c41bf91`

with a clean working tree before and after and **no source/test edits during
validation**.

Recorded evidence:

- Python compile smoke: PASS.
- Core focused update/support suites: PASS.
- High-fanout stale-fixture regression set: PASS (14/14 suites).
- Second-validation regression set: PASS (candidate-support streaming,
  bootchain, devproof, devrun3).
- Full `test_lifecycle.py`: PASS (74 tests).
- `git diff --check 67c7c445..44927e37`: PASS.
- documentation-routing checks: PASS.
- `make verify`: **PASS**, exit 0.
- Full suite result: **3589 tests OK, 4 skipped**, 451.024 s.
- validate, shell-check, footprint and final clean-bytecode stages: PASS.
- Full local log was captured at
  `/tmp/greia-r4-closure-make-verify.log` on the validation host.

No installer, Greia root, release image, debootstrap, real QEMU, mount/loop,
media write, Docker, Orbiter, or physical hardware action was part of this
closure validation.

The commits after `44927e37` that record this result are documentation-only
closeout commits; the validated source/test tree itself is exactly
`44927e37dcb150d9fb6cbad7226a52c35c41bf91`.

### Current routing

**Session 03 — owner release CLI + compact release outputs is now the next
engineering session.**

Do not reopen R4 unless a new concrete regression is found. Physical Acer
install/update/rollback acceptance remains later binary-release certification
evidence; it is not a prerequisite for Session 03.

## 38. Session 03 owner release CLI — source implementation ready for local validation (2026-09-20)

Session 03 has moved from planning into implementation. The current source
tranche introduces the one-command owner release architecture while preserving
all lower-level owners rather than forking another build pipeline.

### Implemented

- `tools/greia_release.py` with `build`, `doctor`, `build-profile`,
  `inspect` and `write-media`.
- Current release matrix contains only the real
  `acer-aspire-one-i386-ab` profile; the output/report schema is already
  multi-platform compatible.
- Normal build version must match repository `VERSION`, preventing composed
  root metadata and bundle version drift.
- `doctor` checks Linux/x86_64/root status, required host tools, typed profile
  + package-set/builder support, and workspace capacity on the selected output
  filesystem.
- Persistent apt/pool caches live beside the chosen output under
  `.greia-cache`; per-attempt scratch lives under `.greia-work`.
- `build/compose-release-profile.sh` owns target + live composition,
  hardware-support population while the live chroot environment is active,
  and bounded mount teardown. Python owns no mount bookkeeping.
- Direct `build/lib/compose.sh` execution was also corrected to own teardown;
  sourced image-builder consumers keep their existing outer cleanup.
- `tools/build_release.py build-payload` may now omit the low-level
  `--minimum-slot-bytes`; the producer derives it from the real shrunk ext4
  bytes plus `PAYLOAD_MIN_HEADROOM`. The explicit parameter remains a
  developer/test override.
- The owner CLI passes the resulting payload receipt into
  `tools/greia_update.py build`; it does not hand-copy payload
  uncompressed/minimum facts.
- Successful publication is atomic from a scratch `publish` directory into
  `out/greia-<version>/`. Failure preserves scratch and never creates the
  final release directory.
- `release-report.json` records source commit, profile/layout facts,
  target/live apparent bytes, bundle/payload/support sizes and SHA-256,
  portable producer facts, exact published-directory byte accounting, and an
  explicit deferred universal-Setup entry rather than a fake image.
- Durable per-profile build log and compact payload/support intermediates live
  under `intermediate/<profile>/`.
- `write-media` delegates to the existing safe writer and preserves its
  interactive exact-device confirmation; Session 03 itself produces no Setup
  image.

### Validation boundary

No real release/root/installer build has been run as part of this source
implementation. The exact local-agent brief is:

`docs/testing/2026-09-20_SESSION03_RELEASE_CLI_LOCAL_VALIDATION.md`

It permits only py_compile, bash syntax/static checks, fake-runner/unit suites,
diff hygiene and the existing source-level `make verify`. It explicitly
forbids `greia_release.py build` / `build-profile`, direct composition,
debootstrap, real QEMU, mounts/loops, media writes, Docker, Orbiter and physical
hardware work on the owner's local machine.

Current routing: run that source validation. If green, Session 03 still needs
one real one-command Acer release build on the appropriate supported x86_64
Linux build host before Session 03 can be called fully complete. Do not move
the real artifact build onto the owner's local machine.

## 39. Session 03 first source validation — canonical-path test repaired; rerun pending (2026-09-20)

The first Session 03 source validation ran at exact HEAD
`8dd2d8c436202555a7d5966130c2846aea8804b8` with a clean tree before and
after and no prohibited build commands.

Evidence from that run:

- py_compile: PASS;
- bash syntax: PASS;
- 7/8 declared focused suites PASS;
- `test_greia_release.py`: 10/11 PASS with one deterministic failure;
- `git diff --check`: PASS;
- `make shell-check`: PASS;
- full `make verify`: 3601 tests run, failures=1, skipped=4;
- the same single test failed in both focused and full execution.

The failure was not a release-orchestration defect. On macOS,
`tempfile.TemporaryDirectory()` may expose a path under `/var/...` while
`Path.resolve()` canonicalizes it through the system symlink to
`/private/var/...`. Production `ReleasePaths.for_release()` intentionally
canonicalizes the selected output root with `expanduser().resolve()`, so the
CLI correctly returned the canonical output path while the test compared it
against the unresolved temporary-path spelling.

Repair commit:

`dc36cfc93f01d5a9a3085421c499aa5b6d3c3e62`

The repair changes tests only:

- `test_paths_use_final_release_schema` now explicitly asserts that
  `output_parent` is canonicalized;
- the normal-build orchestration test compares the returned output path to
  `release_root.resolve()`.

No production source/build behavior was weakened or changed.

Fresh execution against `dc36cfc9...` is still required before Session 03
source validation is called green. The owner-machine boundary is unchanged:
no real release/root/installer build, debootstrap, real QEMU, mounts/loops,
media writes, Docker, Orbiter or physical hardware work.

If the corrected source validation is green, the remaining Session 03 closure
step is one real owner-CLI Acer release build on an appropriate supported
x86_64 Linux build host. Session 04 remains closed until that artifact exists.

## 40. Session 03 corrected source validation GREEN; Linux owner-build acceptance next (2026-09-21)

The owner returned the corrected Session 03 source-validation result after the
portable canonical-path test repair:

- full source suite: **3601 tests OK, 4 skipped**;
- `make verify`: PASS;
- project validation: PASS;
- all 41 Activity validations shown by the project validator: PASS;
- source footprint completed;
- final clean-bytecode completed.

The original single failure was therefore isolated to the macOS
`/var` -> `/private/var` path-spelling assertion and is closed by
`dc36cfc93f01d5a9a3085421c499aa5b6d3c3e62`. Production
`ReleasePaths.for_release()` continues to canonicalize owner output paths;
the test now asserts that intended contract.

No real release/root/installer build was part of this source validation.
Session 03 now has one remaining closure predicate: execute the real owner
release command on a supported x86_64 Linux build host and inspect the
resulting release report/bundle without manually reconstructing the low-level
pipeline.

Canonical procedure:

`docs/testing/2026-09-21_SESSION03_LINUX_RELEASE_BUILD_ACCEPTANCE.md`

That procedure deliberately calls the result a **Greia release directory with
the current Acer-only matrix**, not an Acer installer. The one universal Setup
image remains a later Session 08 product after amd64 and ARM/Pi boot paths
exist.

Session 04 remains closed until the Session 03 Linux owner-command build is
green.

## 41. Session 03 first Linux owner build exposed live-media identity ordering defect; repair pending rerun (2026-09-21)

The first real Session 03 owner-command build ran on the Orbiter x86_64 Linux
host at exact source:

`65af8805faf00f1218abb5dbf0bd562a692426bd`

Pre-build evidence was clean:

- HEAD == origin/main;
- tree clean;
- focused `test_greia_release.py`: 11/11 PASS;
- `greia_release.py doctor`: PASS, all 6 checks green;
- no prohibited actions.

The owner command failed before publication while composing the live-installer
root. The Debian i386 kernel postinst invoked `update-initramfs`; the
Greia-owned fail-closed
`build/installer-overlay/etc/initramfs-tools/hooks/greia-live-media-id`
correctly refused because `/etc/greia-os/live-media-id` did not yet exist.
The resulting kernel/meta-package dpkg errors were downstream consequences.

Root cause: the older `build/build-installer-image.sh` consumer already knew
that live-media identity must be seeded before kernel package installation,
but the shared `compose_root(... role=live-installer)` path introduced by the
Session 02/03 refactor had not absorbed that prerequisite. The release adapter
uses the shared composer, so the hidden consumer-only ordering dependency
surfaced only in the first real owner build.

Repair commits on current main:

- `05d058c3` — add shared `compose_prepare_live_media_identity` and invoke it
  in the generic live-installer composition path before package installation;
- `9a187baf` — make `build/build-installer-image.sh` use the same helper
  instead of owning a second UUID-generation implementation;
- `1c5bb376` — add source-contract regression coverage for shared ownership and
  pre-kernel-postinst ordering;
- `a6fd434a` — tighten the helper so identity is root-local: repeated calls
  preserve a valid existing root identity, while a fresh root gets a fresh
  UUID; the exported shell variable is output only for immediate outer-media
  assembly.

The hook remains fail-closed. No package postinst is bypassed, no hook is
weakened, and no Session-03-specific special case was added to the release CLI.

The failed build scratch/evidence at the old SHA was intentionally preserved;
there were no leftover build mounts and the source tree remained clean.

Current state: **repair implemented, validation pending**. On Orbiter, pull
current main, run shell syntax plus focused system-overlay/release tests and
`make verify`. If green, start a **fresh** Session 03 owner-build acceptance
at the new exact HEAD; do not reuse the preserved failed work root.

## 42. Session 03 repaired-source validation blocked by repo-wide verification hygiene; source-hygiene repair pending rerun (2026-09-22)

The first validation of the live-media identity repair at
`99f9588d62380e01537adc4eff09cbd93c065769` stopped correctly before
doctor/build. Shell syntax, the focused release CLI suite (11/11), the focused
system-overlay suite (23/23), and `git diff --check` were green.

`make verify` did not reach the unittest suite. Its initial
`clean-bytecode` target ran repo-wide `find .` commands and descended into
the preserved, root-owned failed Session 03 evidence/work tree under
`tmp/session03-linux-release-65af8805.../out/`. That produced permission
errors in `.greia-cache/apt/partial` and the preserved `.greia-work`
directory. The source tree itself remained clean and unchanged.

This is verification-hygiene fallout, not a product/source test failure.
Deleting/chowning the preserved failed evidence is intentionally not the
solution. Repository verification must tolerate ignored privileged build
evidence living under the checkout.

Repairs on current main:

- `51ec3aba`: bound `clean-bytecode` to source-owned Python trees
  (`src tests tools activities`) plus non-recursive repository-root cleanup;
  it no longer traverses arbitrary ignored build/evidence directories.
- `dfbf8dc8`: regression test preventing restoration of repo-wide bytecode
  traversal.
- `71375f55`: make `build/footprint-source.sh` compute Git-checkout
  “source archive-relevant” footprint from tracked files only, rather than
  `du` over the entire checkout; explicit runtime-payload measurements remain
  unchanged. This also makes the reported footprint semantically accurate.
- `d1f60390`: regression coverage for tracked-only source-footprint behavior.

The old failed Session 03 root must remain untouched. Next validation should
pull current main, prove `make clean-bytecode` and `build/footprint-source.sh`
succeed while that old root still exists, run the focused hygiene test and full
`make verify`, then proceed to doctor + a fresh owner build only if green.

## 43. Session 03 hygiene validation caught Make shell-variable escaping defect; corrected before privileged rerun (2026-09-22)

Validation at `e9ba8f01e16ae3d9912e9d2396e90068eef591d0` stopped correctly in the
focused hygiene suite before `make clean-bytecode`, doctor, or the owner
build. The new `clean-bytecode` recipe had the right source-bounded design
but used single-dollar shell variables (`$root`) inside a Make recipe.
GNU make therefore consumed `$r` before the shell saw it, so the loop would
not have operated on `src/tests/tools/activities` as intended.

The regression test correctly exposed the mismatch by requiring the literal
Make spelling `$$root`.

Repair:
- `972aeb7e` — actual Makefile correction: all three loop references use
  `$$root`, which make passes to the shell as `$root`;
- `30c47909` — strengthen the hygiene regression to assert the directory
  guard plus both `find` calls and exactly three `$$root` references.

An earlier connector write attempt `05cd356f` was a no-op tree-wise because
the patching helper treated `$$` as replacement syntax; it was detected by
re-fetching the blob and did not change source behavior. The effective source
fix is `972aeb7e`.

The preserved root-owned Session 03 evidence remains untouched. Next: pull
current main, rerun the hygiene-focused test, then directly prove
`make clean-bytecode` and `build/footprint-source.sh` succeed with the old
root-owned evidence still present. If green, continue with full
`make verify`, doctor, and a fresh owner build under the new exact SHA.

## 44. Session 03 hygiene test expectation corrected after connector dollar-literal mutation (2026-09-22)

Validation at `d5530b78d9c4bde7e7b302fb3a9d37204c5369a7` stopped correctly in the
focused hygiene test. The Makefile was functionally correct and visibly used
three `$$root` references, but the committed Python regression test had been
rewritten to assert the buggy single-dollar spelling.

Root cause of the repeated mismatch was the GitHub contents write path used by
this session: literal `$$` sequences embedded in the Python test source were
collapsed during the write. The Makefile blob itself retained its intended
`$$root` spelling.

Effective test repair:
- `5f7aaa19` removes literal double-dollar tokens from the Python test source;
  it constructs the expected Make shell variable at runtime with
  `chr(36) * 2 + "root"`, constructs the forbidden single-dollar form with
  `chr(36) + "root"`, asserts all three required escaped references, and
  asserts the three buggy single-dollar forms are absent.

The committed blob was re-fetched after the write and verified to contain the
runtime constructor rather than connector-sensitive literal `$$root` text.
The Makefile remains unchanged and correct.

Next: pull current main, rerun only the focused hygiene test first. If green,
continue with the already-defined direct `make clean-bytecode` and
`build/footprint-source.sh` proofs, then full `make verify`, doctor, and the
fresh Session 03 owner build. Prior privileged evidence remains untouched.

## 45. Session 03 owner build reached hardware-pool population; missing APT metadata ownership repaired (2026-09-22)

The owner build at
`821934af4e387b7b1278a3a2c6736cd5d48db447` passed:

- focused hygiene test;
- direct bytecode cleanup with preserved root-owned evidence;
- tracked-source footprint reporting;
- full `make verify` (3603 tests, OK, 8 skipped);
- release doctor (6/6 checks green).

The previous live-media-id failure did **not** recur. Kernel package postinst and
`update-initramfs` completed successfully, proving the shared live-media
identity repair.

The next real failure occurred later during hardware-support pool population:
APT reported `alsa-topology-conf` had no installation candidate. Debian
Bookworm still publishes `alsa-topology-conf` (Architecture: all,
1.2.5.1-2), so this was not an upstream package removal.

Root cause: `compose_root()` intentionally ends with
`compose_footprint_hygiene()`, which removes `/var/lib/apt/lists/*`.
Session 03 then invokes `populate-hardware-support-pool.sh` after
`compose_root()` returns. That pool producer used `apt-cache` and APT
dependency resolution but implicitly assumed repository metadata was still
present. The traditional installer-image path populated the pool before
footprint hygiene, so the hidden ordering dependency had not been exposed.

The package that surfaced the bug is plausible hardware metadata input:
`alsa-topology-conf` itself owns a file under `/lib/firmware`, so Debian
firmware Contents metadata can classify it as a candidate. The generic issue
is nevertheless missing APT metadata ownership, not that one package.

Repair:

- `70729300` — make `populate-hardware-support-pool.sh` explicitly refresh
  the remote APT metadata it requires before candidate discovery/resolution;
  reuse one bounded network-option set for update/download operations; after
  successful pool finalization restore image hygiene by removing remote APT
  lists again.
- `93675ba1` — readability-only formatting of the refresh command.
- `cf2f0068` — regression coverage locks the lifecycle:
  composer hygiene may remove lists; pool producer refreshes before
  `apt-cache`/download resolution; finalization completes before lists are
  removed again.

This makes the hardware-pool producer a self-contained APT consumer rather
than coupling it to caller ordering. Persistent Greia package caches remain
untouched.

Next: pull current main; run shell syntax plus the focused system-overlay
contract, then full `make verify`. If green, doctor and a fresh owner build
under the new exact SHA. Preserve all previous failed work/evidence roots.

## 46. Privileged release bytecode contamination and false-green cleanup fixed (2026-09-22)

Validation at `3a8a1a221e316230bb507aacccaa56b74261a867` reached full
`make verify`. The unit/validation suite itself was green (3603 tests, 8
skipped), but the final `clean-bytecode` emitted 64 permission errors while
trying to remove root-owned `__pycache__` / `.pyc` files inside
`src/` and `tools/`.

The root-owned bytecode had been created by the prior privileged owner
`doctor/build` invocation: the release CLI imports project modules as root,
and its child shell/Python process tree also inherits the privileged uid.

Two defects were exposed:

1. privileged release tooling was allowed to write generated Python bytecode
   into the developer-owned source checkout;
2. `clean-bytecode` did not propagate failures inside its shell loop, so
   `make verify` returned exit 0 even though final cleanup had failed.

Repairs:

- `712d351a` — privileged `tools/greia_release.py` sets
  `PYTHONDONTWRITEBYTECODE=1` and `sys.dont_write_bytecode=True` before any
  project-local import; the release subprocess environment also explicitly
  carries `PYTHONDONTWRITEBYTECODE=1`, so shell/Python descendants cannot
  recreate root-owned bytecode in the checkout.
- `ed61ddfd` — `clean-bytecode` runs its source-root loop under `set -e`,
  making deletion failures fail the Make target and therefore `make verify`.
- `b106980b` — regression coverage requires cleanup failure propagation.
- `2d5f8645` — release tests lock both early privileged bytecode suppression
  and child-environment propagation.

The already-existing root-owned bytecode is historical generated state, not
source. One explicitly authorized one-time `sudo make clean-bytecode` is
required after pulling this repair. It is scoped by the repaired Make target to
`src tests tools activities` plus non-recursive repository-root bytecode and
must not touch preserved `tmp/`/release evidence.

After that one-time cleanup, ordinary non-root `make verify` must be fully
green. A subsequent privileged doctor/build must be checked to confirm it does
not recreate root-owned source bytecode.

The hardware-pool APT-metadata repair remains implemented but still requires
end-to-end owner-build proof.

## 47. Bytecode cleanup moved to a Python owner; prior dollar-collapse diagnosis corrected (2026-09-22)

Validation at `8717db49fa181c696cdd6be65be17301f3747b4b`
showed that the historical root-owned bytecode was still not removed by
`sudo make clean-bytecode`. The Make recipe had again regressed to
single-dollar `$root` shell references, so GNU make consumed `$r` and the
loop silently operated on `oot`.

A retrospective review identified the actual mechanism behind the repeated
regressions: the GitHub connector was **not** rewriting `$$`. This session's
JavaScript patch code repeatedly used `String.replace(old, replacement)`;
inside a JavaScript replacement string, `$$` is interpreted as a literal
single dollar. That was the source of the mutation. Earlier handover/plan notes
that blamed connector-side dollar collapsing are therefore superseded by this
correction.

Rather than patching the same Make/shell escaping again, cleanup ownership is
now structurally simplified:

- `tools/clean_bytecode.py` is the sole owner of the cleanup root set
  (`src`, `tests`, `tools`, `activities`) plus non-recursive repository
  root bytecode;
- `Makefile: clean-bytecode` delegates directly to that Python owner;
- ignored `tmp/` / `out/` / release evidence is outside its traversal;
- deletion failures raise and therefore fail `make clean-bytecode`;
- unreadable source-tree traversal also raises rather than being silently
  skipped;
- regression tests exercise source scoping, preserved ignored evidence,
  deletion-failure propagation, and walk-error propagation.

Effective commits in this repair tranche:
`c19757a0`, `0ee7e44a`, `a45e4879`, `d8888c1e`, `5a23a49b`,
`02ef7c18`. Earlier transitional direct-`find` commits
`1a931c5c`/`70f6c43a` are superseded by the Python cleanup owner.

The prior privileged-release bytecode prevention remains in place:
`greia_release.py` disables bytecode before project imports and its release
subprocess environment carries `PYTHONDONTWRITEBYTECODE=1`.

Local-agent authority for the remainder of Session 03 should be broader than
the previous passive stop-on-any-defect scripts: the agent may diagnose and
apply bounded, obvious source-local repairs in the active release/verification
path, add/update focused regression tests, run the relevant gates, commit the
coherent repair directly on `main`, and continue. It must still stop and ask
for owner direction before destructive media/device actions, broad
architecture changes, dependency/package-policy changes with product impact,
security/trust weakening, evidence deletion, or ambiguous multi-system design
choices.

Next: pull current main, perform the one-time privileged cleanup through the
new Python owner, prove historical root bytecode is gone, run focused cleanup
and release tests + full `make verify`, then doctor/build. If a small,
unambiguous implementation defect appears, the local agent is authorized to
repair/test/commit it rather than stopping immediately.

## 48. Session 03 owner build reached hardware-support archiving; pool-intermediate ownership repaired (2026-09-22)

- Real owner build on `6935a411` progressed past both old failures with no
  repair needed for them: no `greia-live-media-id` hook failure anywhere in
  the 236K+ build log (live-media identity ordering holds), and the
  hardware-pool APT refresh resolved all candidates including the former
  `alsa-topology-conf` gap (pool population + downloads completed).
- New first failure at the hardware-support archive stage:
  `build-release: unexpected pool top-level files:
  ['available-candidates.txt', 'candidates.json']`.
- Root cause: the repaired pool producer left its candidate-discovery
  working intermediates at the pool top level, while
  `tools/build_release.py::_assert_no_hooks` enforces the fail-closed
  allowlist `{manifest.json, Packages, Packages.gz}` (+ `pool/`).
  Nothing downstream reads those intermediates from the pool root;
  `finalize_hardware_support_pool.py` only consumes the manifest.
- Bounded repair (no validator weakening): `populate-hardware-support-pool.sh`
  now removes `$CANDIDATE_MANIFEST`/`$AVAILABLE_LIST` right after successful
  finalization; overlay regression extended with finalize < cleanup <
  APT-lists-hygiene ordering.
- Validation before commit: `bash -n`, focused overlay suite 23/23 OK, full
  `make verify` 3608 tests OK (skipped=8), exit 0, no FAIL/ERROR/permission
  issues.
- No root-owned source bytecode recreated by doctor or the failed build
  (0 entries after each); prevention repair holds end to end.
- Prior Session 03 evidence roots (65af/99f/e9ba/821934/3a8a1a22) preserved
  untouched.

Next: commit this repair on `main`, push after confirming no concurrent
remote advance, then fresh SHA evidence root, doctor, and owner-build rerun
against the repaired pool producer.

## 49. Session 03 payload capacity defect diagnosed: flex_bg pins resize2fs -M; shrink-capable producer repaired (2026-09-22)

- Real owner build on `248ab0df` cleared pool/archiving (intermediate
  cleanup confirmed in production) and failed only at final bundle
  capacity: required 2405617664 > slot 1610612736.
- Payload-size investigation (read-only on preserved `payload.ext4.zst`):
  container == filesystem extent (1610612736; no dead tail), but the
  filesystem itself spans the full slot with ~472 MiB free while
  `resize2fs -M`/`-P` insist the minimum is the current size.
- Bisected on disposable scratch: 200M/512M images shrink normally, 1G/1.5G
  images refuse any shrink; identical 1.5G image with `-O ^flex_bg`
  shrinks 393216 -> 257690 blocks. Root cause: default flex_bg packs all
  block groups into one flex group and e2fsprogs 1.47 cannot shrink that
  layout, so the producer's shrink step was a silent no-op and the receipt
  recorded full slot size.
- Bounded repair in `tools/build_release.py`: mkfs gains `-O ^flex_bg`;
  new single-owner `_ext4_filesystem_bytes` helper derives the authoritative
  post-shrink extent from `dumpe2fs -h` (strict field validation, fail
  closed) and the producer refuses a container/extent mismatch instead of
  recording `st_size`. No validator weakening; installer-created
  on-device filesystems untouched (never need shrinking).
- Regression: mkfs-argv shape + 5-step command order + strict geometry
  parsing + container-mismatch refusal in `test_build_release.py`;
  new `test_payload_shrink_real.py` (Linux/e2fsprogs-gated) proves a real
  1 GiB image shrinks and the real producer pipeline shrinks a real image
  end to end. Pre-commit `make verify`: 3612 tests OK, exit 0, clean tree.
- No root-owned source bytecode recreated at any stage.

Next: commit/push, then owner-build rerun to re-measure the real payload
receipt before touching support-capacity semantics.

## 50. Hardware-support selected-set capacity semantics implemented, source scope (2026-09-22)

- Committed source tranche (`6c58601e`) splits the finalized-slot proof into two
  stages over one formula owner
  (`require_finalized_slot_capacity`): bundle time proves base +
  reserves with support term 0 (metadata still fail-closed verified);
  fresh-install and update staging prove pre-mutation on the verified
  machine-selected bound.
- New bound owner: frozen per-candidate `dependency_closures` from
  `finalize_hardware_support_pool.py`, validated in
  `hardware_support_archive.py`, summed by
  `VerifiedHardwareSupportPool.selected_installed_bytes` (union,
  de-duplicated; empty binds 0; missing/unknown refuses, never
  whole-pool fallback).
- Fresh install resolves selection from the same attested snapshot
  (`InstallerHardwareEnablementPlanner` `inventory_snapshot` replay),
  ceiling-checks selected <= image-authorized whole-pool
  `GREIA_AB_SUPPORT_INSTALLED_BYTES` (`total_installed_bytes`), threads
  selected bound through `SlotFinalizer`. Installer image reports
  `total_installed_bytes`, not compressed bytes.
- Update staging adds `support_pool_factory` (same open stage, no second
  extraction); preflight runs after selection and threads the selected
  number through `SlotWriter` + finalization.
- Tests updated: closure finalize/selection suites,
  `test_release_cli_finalized_capacity.py` (bundle-accept +
  tamper-refusal, base/reserves vs selected split),
  `test_system_update_service_orchestration.py` harness
  (`dependency_closures` + `support_pool_factory`),
  `test_update_seam_composition.py` (closure pool, production
  `support_pool_factory` assertion, selected-bound regression).
- Targeted suites green: `test_update_*.py` 104 OK,
  `test_system_update*.py` 58 OK, `test_installer_*.py` 251 OK,
  `test_fresh_ab_install.py` 29 OK,
  `test_release_cli_finalized_capacity.py` 11 OK,
  `test_update_seam_composition.py` 17 OK.

Next: commit/push on quiet remote, then
owner-build rerun to re-measure the real payload receipt and exercise
the selected-set path. Session 04 remains closed.
- Pre-commit `make verify`: 3618 tests OK (skipped=8), exit 0.

## 51. Session 03 CLOSED on real owner release build (2026-09-23)

- Successful source SHA: `6c58601eaad32ad2bba30acb24e33333b9c4bbf3`
  (`origin/main` in sync, ahead/behind 0 0, tracked tree clean before).
- Version: `0.13.0-phase0-dev`. Evidence root:
  `tmp/session03-linux-release-6c58601eaad32ad2bba30acb24e33333b9c4bbf3/`
  (new SHA-specific root; no earlier evidence deleted; no earlier
  `.greia-work` reused).
- Doctor: exit 0, `ok=true`, all checks green,
  `acer-aspire-one-i386-ab` present. No root-owned source bytecode after
  doctor.
- Owner build: exit 0, `status=complete`,
  `source_commit == SOURCE_HEAD`. No bounded defect encountered; no
  repair loop needed.
- Payload (real, proves the flex_bg/geometry repair):
  compressed=383881888, uncompressed=1110081536,
  minimum=1111130112,
  sha256=c9b58aee72e058c288204e1bb1136859a8d8d8807f21a66178789982a4b3f543.
  Old broken uncompressed 1610612736 is gone from the production
  artifact.
- Bundle `updates/acer-aspire-one-i386-ab.greiaupdate`: 540126645 bytes,
  sha256=6b5cf05f6ad81979fc9bd53c4f1ae1491da024eaf436aabe31e35779f4860a67.
- Hardware support: packages=58, compressed=156244008,
  whole-pool-installed=710070272 (ceiling only, not the machine
  footprint), dependency-closures=37, pool suite=bookworm arch=i386,
  archive sha256=f228a314383bec838aed06fc808bd564dc85c96ac70537a3163918313842c24e.
  Archive top levels are exactly `manifest.json`, `Packages`,
  `Packages.gz`, `pool/` (no `candidates.json` /
  `available-candidates.txt` leakage). Build log has no live-media-id
  or APT-candidate regression markers.
- Inspect report: PASS (exit 0). Inspect bundle: PASS via privileged
  read (exit 0); the bundle publishes root-owned mode 600, so the
  unprivileged acceptance-draft command cannot read it — inspect content
  itself is valid v3 with matching payload/support hashes.
- Consistency: PASS (status, source_commit, public artifacts, deferred
  setup session 8, all five Acer artifacts present and SHA256-matched,
  no `.greia-work` in portable report data).
- Transient work: clean (no entries under `$OUT/.greia-work`).
  Leftover mounts: none. Tree: clean, HEAD unchanged
  (`6c58601eaad32ad2bba30acb24e33333b9c4bbf3`). No root-owned source
  bytecode after build.
- Universal Setup image remains deferred to Session 08. No QEMU, no
  Setup image, no physical media (out of Session 03 scope).

Session 03: CLOSED. Session 04: OPEN.

## 52. Public website concept exploration (2026-09-23)

Three standalone website mocks were added under `docs/design/website_mocks_2026-09-23/`: Storybook, Constellation, and Activity Fair. They use existing canonical cast art, Activity icons, Greia's Nunito font and source palette. The pages are DESIGN SPEC / DESKTOP VISUAL REVIEW only; they do not change the child Shell, Greia Parents, Activity runtime, release readiness, active architecture-remediation phase, Encyclopedia E4 route, or Session 04 lifecycle route. Chromium desktop and mobile mock rendering and the two interactive controls were checked as recorded in the mock README.

## 53. Public website concepts revised after owner feedback (2026-09-23)

The first three mock versions were superseded after the owner requested a more dynamic, modern and playful result and identified the missing canonical Greia boot logo. The current comparison page at `docs/design/website_mocks_2026-09-23/index.html` leads to three rewritten concepts: The Portal (actual boot-frame replay and scroll-linked product chapters), Orbit (six-character spatial selector with keys/drag), and Play Lab (boot-screen entrance, drawable canvas and four switchable worlds). All use `assets/boot/frames/frame_0051.png` or the canonical white boot composition; the product images are historical development Simulator captures, not new acceptance evidence.

Chromium visual and interaction checks covered desktop 1440×900 and mobile 390×844 and 320×700. Images loaded, page errors and horizontal overflow were absent, and the main controls were exercised. Evidence is DESIGN SPEC / DESKTOP VISUAL REVIEW only. No Greia OS implementation, runtime gate, install/update/release state, Encyclopedia E4 state or hardware proof changed. The visual workstream's next runtime action remains the existing E4 continuation when that route resumes; the current lifecycle route remains Session 04.

## 54. Public website third design pass (2026-09-23)

After a second owner rejection of conservative/basic page structures, the website exploration at `docs/design/website_mocks_2026-09-23/` was rebuilt again. The current chooser leads to Worlds in Motion (five full-screen illustrated Greia scenes), The Wonder Map (draggable/zoomable four-world atlas and detail sheets), and The Scribble Machine (page-wide pointer drawing, colour, cast stickers, clearing and four switchable worlds). This replaces the second-pass Portal / Orbit / Play Lab structures as the current design review target. The real boot artwork, accepted character renditions and historical development Simulator captures remain the visual sources.

The user-identified sketch failure was fixed: all words around and underneath the drawing area are non-selectable; native image dragging is cancelled; the canvas uses pointer capture and touch-action control. A Chromium stroke across the large headline produced ink pixels with an empty browser text selection. Desktop and mobile captures were inspected; 1440×900, 390×844 and 320×700 checks found no missing loaded images, JavaScript page errors or horizontal overflow. Story navigation, map dragging/detail open-close, sketch stamps/world switching/Clear were exercised. The mock README lists the exact site references and control behavior. Evidence remains DESIGN SPEC / DESKTOP VISUAL REVIEW; no production web deployment or Greia OS implementation, Simulator acceptance, physical-device proof, Encyclopedia E4 or lifecycle phase change occurred.

## 55. Public website first-concept parent refinement (2026-09-23)

The owner chose the first concept's navigation for major refinement, with parents as the primary audience. `docs/design/website_mocks_2026-09-23/storybook.html` is now a seven-chapter parent story covering child-first purpose, reusing older hardware, the x86/ARM mission, Greia's Activity/platform/hardware layers, Greia Parents, personalized Activity ideas and the Creation Pack direction, prerecorded character voices, and the open project. Its new CSS/JS provides an automatic skippable/replayable sequence of all 52 original boot frames, chapter navigation and reveal motion, device/architecture/Parent/idea controls, and click-to-play accepted English voice intros. A real Parent app development capture joins the historical Greia Shell capture.

The actual boot logo has a large hero and ending treatment plus a persistent small horizontal identity. The external `GREIA_BOOT_ANIMATION_LOCAL_AGENT_PATCH_2026-08-17` held rendered frames and Plymouth code but no editable SVG, so the isolated transparent G and Greia wordmark were recreated from `assets/boot/frames/frame_0051.png` as website-only exploratory SVGs. The canonical boot frames are untouched; these SVGs are not accepted shared brand masters. Copy identifies contributor tools and controlled installation as current development paths and the guided family Creation Pack/ordinary-release install as still in development.

Chromium visual review covered all seven chapters at 1440×900 and mobile layouts at 390×844 and 320×700. Interaction checks exercised the intro, navigation/menu, device/layer/Parent switches, illustrative Activity options and a real Lilli voice clip. A final 320-pixel check found no horizontal overflow or broken loaded images; `node --check` passed for the new script. `storybook-preview.png` and `storybook-overview.png` are review aids. Evidence is DESIGN SPEC / DESKTOP VISUAL REVIEW for the local mock only. The other two website concepts, Greia runtime, production deployment, physical-device proof, Encyclopedia E4 and the install/release phase remain unchanged. Next website step is owner review of the first concept's visual and narrative direction.

## 56. Public website first-concept night landscape and parent guide (2026-09-23)

The owner rejected the first concept's white intro, weak small logo and shallow parent-facing content. The current review target is `docs/design/website_mocks_2026-09-23/storybook.html`. It expands the original boot scene into a full-width authored SVG night with mountains, trees, village lights, flowers, stars and fireflies; the unchanged 52 boot PNGs animate in the centre before the interface fades in. Replay/skip and reduced-motion routes work. The website-only transparent mark/lockup derivatives were strengthened for small use, with thicker paths and crisp star centres; they are not accepted canonical logo sources.

The revised page has twelve historical Greia Shell/Activity screenshots with filters and enlargement, explicit old Acer and Pi 400/500 mission and hardware context, four interactive architecture layers, Parent app controls and an enlargable real development capture, personalized Activity concept choices, a carefully scoped Creation Pack explanation, all six accepted English character introductions and eight FAQs. Copy separates current development capabilities from incomplete release/family acceptance. The other two concepts remain available through the updated chooser. `storybook-preview.png`, `storybook-overview.png` and `index-preview.png` were regenerated.

Chromium checks at 1440×900, 390×844 and 320×700 exercised gallery filters/navigation/lightbox, Parent capture enlargement, hardware/architecture/Parent/idea controls, FAQ and actual Lilli audio. All twelve gallery image paths and loaded images resolved; there were no page errors or horizontal overflow. A normal-motion intro reached frame 52/52 and replay/skip passed; reduced-motion runs finished immediately. `node --check` passed. Evidence is DESIGN SPEC / DESKTOP VISUAL REVIEW of the local website mock only. No Greia OS runtime, production website, physical-device, Encyclopedia E4 or install/release phase state changed. Next website step is owner review of this rebuilt first direction; the existing Encyclopedia and platform continuation routes remain as recorded above.

**Repository gate:** `make verify` was run on this macOS checkout before commit. It ran 3,646 tests and exited 2 with three errors and one failure, all in `tests/test_x8_qemu/test_session04_legs.py`; the four tests call the Linux-only product lifecycle gate and receive `BLOCKED product mode: device lifecycle requires a Linux host (this host reports darwin)`. A focused rerun of that module reproduced exactly 3 errors/1 failure in 18 tests. This is a host/test boundary failure, not a passing verification claim and not website-specific. The browser checks above remain the mock evidence.

## 57. Official Greia website work in progress (2026-09-23)

The owner promoted the first parent-facing website concept to the official site work in progress. Its source is now `website/index.html`, with `website/downloads.html`, `website/library.html` and `website/README.md`. The old `docs/design/website_mocks_2026-09-23/storybook.html` URL redirects to it; `storybook-historical.html` preserves the last mock, and the other historical design experiments remain available. This is a standalone local static site, not a production deployment or installer release.

The homepage explains first that Greia is a complete child-focused Linux operating system. It keeps the authentic 52 boot frames in a full Greia night scene, fades in the interface, and runs a bounded swarm of fireflies that continuously drift and gently follow nearby pointer movement. Nunito display headings now use natural glyph spacing; the desktop hero logo no longer collides with the headline. Ten selected English real-service Simulator captures cover the Shell and Activities; the only Italian screenshot is the explicit English/Italian Encyclopedia comparison. The Parent enlargement opens one readable 1024×600 development-client viewport. Six accepted prerecorded character introductions remain playable.

The parent story now covers reuse of early netbooks and other PCs, Pi 400/500 practicality as first-class ARM targets, per-device verification, Greia's layered architecture, local-network Parent management without a general child browser, agent-oriented Activity authoring/parent approval, authoring-time voice generation for pre-readers, and possible low-cost use by schools and communities including lower-income regions. It distinguishes current contributor tools and development captures from the planned installable family Creation Pack and unfinished release gates. The source repository, Activity authoring skill, download status and Activity library are linked prominently.

The Downloads page has device-specific installer controls, disabled until real verified artifacts exist. The Activity library has eight manifest-matched source Activity previews, filtering/search/details and per-Activity package controls; all remain disabled until reviewed `.greiaactivity` URLs are published. There is no claimed public installer, package, production website or ordinary-family acceptance.

Local Chromium checks covered all three pages at 1440, 1024, 768, 390 and 320 px widths with no broken images, horizontal overflow or page errors. The homepage gallery filter/lightbox, Parent single-screen enlargement, hardware/Parent/idea switches, voice loading, normal intro/replay/skip, continuously moving fireflies and pointer response passed. Library search/filter/details and one-record package enablement passed; all unpublished release controls stayed disabled. The old first-concept URL redirected correctly. All 52 copied boot PNGs were byte-identical, all eight library IDs matched source manifests, and `node --check` passed for the three JavaScript files. Evidence is DESIGN SPEC / DESKTOP VISUAL REVIEW for the website and development SIMULATOR VISUAL REVIEW for the selected English captures only; it does not advance Greia runtime, physical-device, Encyclopedia E4, public-source or release evidence.

Next website step: review the three local site pages with the owner, then refine the accepted visual/message direction; activate installer and package links only after exact artifacts, tested device scope and publication gates are recorded. Greia's existing blocking architecture, visual Encyclopedia and Session 04 lifecycle continuation routes remain as recorded above.

**Repository gate on this checkout:** `make verify` ran 3,646 tests on macOS and exited 2 with 2 failures/3 errors/6 skips. Four outcomes are the known `tests/test_x8_qemu/test_session04_legs.py` Linux-only product-host boundary (`BLOCKED ... this host reports darwin`). The fifth was `test_t3_update_production.LauncherProductionCallTests.test_apply_accepts_first_install_through_production_seam_exactly_once`, which timed out reading a root boot-health response during the broad run; after bytecode cleanup, that exact test passed in a focused rerun (1 test, 1.165 seconds). No website-specific browser check failed. This is not a full repository verification PASS; the lifecycle product tests require the named Linux host.

## 58. Official website opening rebuilt from original high-resolution boot render (2026-09-24)

The owner rejected the official website's guessed night landscape as visually inconsistent with the real boot art. Investigation of `/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/GREIA_BOOT_ANIMATION_LOCAL_AGENT_PATCH_2026-08-17` found rendered 222×600 frames and Plymouth playback/verification code, but no editable drawing source. The original 1080×2922 rendered sequence was found in `/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/greia_boot_7fps_1080x2922/`. The official homepage now displays that source's final frame at full resolution after the unchanged 52-frame playback; its star G, Greia lettering and central forest are original rendered pixels. A website-only panoramic extension uses that final frame as its reference and follows its dark navy colors, fine mountain lines, dense pointed pines, small lit houses and lilac flowers. The previously guessed wide SVG was removed from the official site. Exact file hashes and the derivative boundary are recorded in `website/README.md`; the OS boot assets and historical design studies were not changed.

This is website **DESIGN SPEC / DESKTOP VISUAL REVIEW**, not a reconstructed original vector master or OS/hardware acceptance. The active Encyclopedia, R7 and install/release routes remain as previously recorded. Next website step is owner visual review of the corrected first screen; verified installer and Activity package publication remain separate gates.

Source checks: the copied high-resolution final frame has the same SHA-256 as the discovered original; the derived panorama is 1672×941, and `node --check website/site.js` plus `git diff --check` passed. The corrected opening was visually inspected from earlier local 1440, 1024, 390 and 320 px captures; the final mobile CSS adjustment moved only the original-frame layer upward to clear its wordmark from the headline. A further live in-app browser open of the local `file://` site was rejected by browser URL policy, so no post-adjustment browser run is claimed. The previous full `make verify` limitations on macOS remain as recorded in entry 57; this visual-only website tranche did not rerun OS verification.

## 59. Session 04 install-leg diagnosis handover (2026-09-24)

Session 04 remains OPEN, blocked on the fresh-install EXECUTE leg in product-mode QEMU: the install service stops responding (empty socket response, never a refusal) after streaming slot A and writing fstab, before GRUB/persist/journal work. Same signature across attempts 5–11 at 2 GB and 4 GB guest RAM. Host-side full service-stack reproduction with the exact Session-03 artifacts completes in ~66 s, so this is environmental, not a product-logic defect found so far. Two real product bugs were found and fixed along the way (support-classes narrowing, `1ecba9de`; installer USB sizing/bytecode, `6c13abea`).

Full evidence, ruled-out theories, open hypotheses (ranked) and exact next steps are recorded in `docs/testing/2026-09-24_SESSION04_INSTALL_EXECUTE_FAILURE_DIAGNOSIS.md` with machine-readable facts and the serial log in `docs/testing/session04-evidence/`. HEAD carries two TEMPORARY diagnostic commits (`3f101b1c`, `0acc0f05`) that must be reverted before closure. Next agent: fix the faulthandler fd lifetime, try the sandboxed host repro, then strace-via-unit if needed — details in the report §8.

## 60. Session 04 root cause and security decision (2026-09-25)

The faulthandler file-handle lifetime is now corrected with a module-owned serial reference and a 120-second repeating interval. Marker-gated socket-boundary logging and a test-only final service-status capture were added. Focused evidence passed: 45 transaction-service tests, 20 Session-04 harness tests, and 38 product-install harness tests.

The rebuilt diagnostic installer was inspected from its live SquashFS and matched the S03 bundle/support facts. A final product-mode QEMU install reached `finalize-completeness` with the service active, 2/8 tasks, and approximately 1.74 GiB available. The final guest journal proved the failure at `src/greia_installer/hardware_support_install.py:61`: apt in the mounted slot failed `setgroups`, `setegid`, and `seteuid` with `Operation not permitted`; systemd recorded `Result=exit-code`, `ExecMainStatus=1`. The client empty response is a consequence of that failed service request, not a proven external SIGKILL.

The full decision record is `docs/testing/2026-09-25_SESSION04_INSTALL_EXECUTE_ROOT_CAUSE_AND_DECISION.md`. Follow-up review found a second service-topology defect: the shipped unit executed `transaction_service` with `python -m` while composition re-imported that same implementation canonically, allowing split `__main__`/package module and exception identities. The repair is now landed: a thin `transaction_service_entrypoint` executes the canonical library module, the implementation is library-only, and the unit adds only `CAP_SETUID`/`CAP_SETGID` alongside the existing `CAP_SYS_ADMIN`/`CAP_SYS_CHROOT`; `NoNewPrivileges=yes` and `ProtectSystem=strict` stay intact. Permanent unit-contract tests pin this architecture. These source changes still require Orbiter focused tests, installer rebuild/inspection and product-mode QEMU. Session 04 remains OPEN; temporary diagnostics stay until one confirming install and must be removed before closure.

## 61. Post-GitHub Orbiter validation reached a new security boundary (2026-09-25)

The repair ancestor `06341ad49cc6b7ff9ed5bda4ad8919051bceb9d4` is present in
`46a654fdc27acd20193285c702fb2761911c8936`; `HEAD == origin/main`, the tree was
clean before validation, the immutable S03 bundle SHA matched, and Orbiter had
84 GB free. The required focused suites passed: 23 unit-contract, 46
transaction-service, 13 seam-composition, 20 Session-04 legs, and 38
ProductHarness install tests.

A new diagnostic installer was built from the unchanged S03 bundle and
verified in the built live SquashFS: canonical entrypoint, library-only service
implementation, exact four-capability unit, `NoNewPrivileges=yes`,
`ProtectSystem=strict`, embedded bundle SHA, 58 support packages, 710070272
support ceiling, and no bytecode. The first confirming run then exposed a
missing target-chroot `/dev/pts`; the shared `dev/proc/sys/run` mount helper
was added. The next run reached apt package configuration but cleanup left
recursive binds busy; normal-then-lazy detach was added and regression-covered.
The latest clean diagnostic run is captured in
`docs/testing/session04-evidence/post-repair-04-cap-chown-refusal.log`.

The latest run now fails after apt package configuration with:

```text
chown to _apt:root of directory /var/cache/apt/archives/partial failed
SetupAPTPartialDirectory (1: Operation not permitted)
```

This is beyond the already authorized exact four-capability contract. The next
repair requires an explicit decision to add `CAP_CHOWN` or change apt's
privilege/ownership behavior; no such change has been applied. The temporary
control response trace, diagnostic service code, and chroot mount repair remain
in the working tree for the decision handoff. The blocked QEMU was stopped; no
Session-04 mounts or loops remain, and approximately 73 GB was free at the
last cleanup. Session 04 remains OPEN; no lifecycle leg or clean-build
acceptance has started.

## 62. Session 04 apt ownership decision report (2026-09-25)

The detailed decision brief is `docs/testing/2026-09-25_SESSION04_APT_OWNERSHIP_DECISION.md`.
It records the exact four-capability contract, the proven `chown _apt:root`
failure, Option A (`CAP_CHOWN`), Option B (apt ownership/privilege policy), the
security tradeoffs, acceptance criteria, and the explicit requirement not to
silently extend the capability contract. No option has been applied. Another
agent should review that report before authorizing the next repair.


## 63. Session 04 CAP_CHOWN decision corrected after APT source review (2026-09-25)

The apt-ownership decision at `bf1b08e1` was too strong. The preserved QEMU refusal showed an early `SetupAPTPartialDirectory` chown warning, but the production package runner truncated stderr to its first 256 characters. Debian APT treats that failed chown as a warning and continues, so it did not prove that missing `CAP_CHOWN` caused the non-zero package command.

No fifth capability is authorized. GitHub follow-up changed the bounded package failure detail to preserve both stderr head and fatal tail. It also replaced the newly added normal-then-lazy chroot cleanup with one shared recursive fail-closed cleanup owner used by the fresh installer, legacy installer and update package path; failed roots remain tracked instead of being erased.

Next Orbiter action: pull current `main`, run the focused installer/update suites, rebuild the diagnostic installer from the unchanged S03 bundle, and rerun **fresh install only**. The next decision must be based on the actual fatal stderr tail. Session 04 remains OPEN and temporary diagnostics remain until the confirming install is green.


## 64. Orbiter hardware stop — failing /dev/sda (2026-09-25)

Session 04 validation is paused for infrastructure safety. At source HEAD `c8054717844840e2268d9abecd62da818ad60ef6`, all nine focused suites passed and the immutable S03 bundle plus all four Session-04 candidate digests re-verified. The diagnostic installer rebuild then failed after `mksquashfs` reported success but `unsquashfs` could not read a valid SquashFS superblock.

Orbiter kernel logs show repeated current `Medium Error` reports from its only disk, `/dev/sda` (SAMSUNG HN-M500MBB), including errors during the 2026-09-25 build and earlier bursts. Treat Orbiter's root disk as failing hardware. Do not run further debootstrap, mksquashfs, QEMU lifecycle, destructive disk diagnostics, or other heavy Session-04 I/O against that disk.

The Git repository is preserved remotely on GitHub at `c8054717`. The irreplaceable local evidence that must be copied to healthy storage before more work is the exact Session-03 release root (including bundle/payload/hardware-support intermediates if present), the four verified Session-04 candidate bundles, and any uncommitted local-only Session-04 evidence. After copying, re-hash against the recorded SHA-256 values before resuming. Prefer a fresh clone from GitHub on healthy storage rather than copying the working tree from the failing disk.

Session 04 remains OPEN. The current software next step remains the fatal-tail fresh-install rerun, but only from healthy storage/build media.

## 65. Orbiter host disk failure and full-disk migration (2026-09-25)

Session 04 validation was executed correctly and then hit an environmental blocker: the Orbiter root disk (SAMSUNG HN-M500MBB serial `S2R7J9HB601575`) is in hardware failure — SMART `FAILED`, "Drive failure expected in less than 24 hours", `Raw_Read_Error_Rate` FAILING_NOW, 2 pending sectors matching the two persistent bad regions. The diagnostic installer build died on an `unsquashfs` read-back (`Input/output error` / invalid squashfs superblock) caused by sector 710844416. Kernel journal shows the first Medium Errors at 2026-09-15 02:05, before the heavy Session-03/04 build churn — root cause is hardware, not source and not loop/mount operation; agent practice nevertheless amplified load and leaked 17 attached `PIP_ROOT` loops with deleted backing files (sidebar litter, ~35–45 GB pinned, desktop probe reads). Full evidence, honest causation analysis, and binding prevention rules: `docs/agents/2026-09-25_ORBITER_DISK_FAILURE_INVESTIGATION.md` (rules also in `docs/agents/GREIA_AGENT_OPERATIONS.md` §12).

Before the failure, all 9 focused suites at `c8054717` passed (seam 14, cleanup 6, engine 18, hardware 3, unit-contract 23, transaction 46, S04-legs 20, product 38, update-seam 17); S03 bundle SHA and all four candidate SHAs verified. Session-04 procedure §11 stands: next action remains diagnostic build + **fresh install only** with fatal-tail capture; no capability decision is pending from this environmental stop.

Migration is **complete and verified** (owner-ordered): replacement drive serial `S2R7J9HB601552` (SMART PASSED, 88 h, USB-3/UAS) was wiped, given a GPT cloned from the source (identical partition GUIDs `bb7e800d…`/`e5a2bbe1…` so NVRAM `Boot0001* Ubuntu` survives), formatted with cloned filesystem UUIDs (`7893f386…` root, `9BFE-A487` ESP) so fstab/ESP stub/grub/initramfs need no edits. `rsync -aHAX` pass 1 copied 376.3 GB / 1,063,266 files in 2 h 53 m; pass 2 caught up +6.4 GB; the only real casualty was `Long-John-Silver/data/ljs.db` (one physically dead 64 KiB zone on the source — repaired file kept plus a per-table salvage `ljs.recovered.db` with integrity ok / 446,119 rows / 49 tables; 3 vec0-extension exceptions documented). fstab and ESP byte-identical; `fsck -nf` and `dosfsck -n` clean on unmounted filesystems; everything cleanly unmounted. Full record: §8 of `docs/agents/2026-09-25_ORBITER_DISK_FAILURE_INVESTIGATION.md`. A transient USB/UAS link drop on the target enclosure early in the transfer recovered by itself and never recurred.

**Next exact step: owner powers off and physically swaps the disk in the Mac mini** (procedure in report §8.4), then per below.

**Next exact step after reboot on the new disk:** confirm SMART of the installed drive, detach any state, pull `main`, then resume the Session-04 procedure at its §3 (rebuild diagnostic installer from the unchanged S03 bundle; fresh install only with fatal-tail evidence). Do not reopen the capability question without a fatal tail.

## 66. Acer A/B GRUB installer physical boot failure (2026-09-27)

The Acer/legacy-i386 installer built and flashed on 2026-09-26 **does not boot on the
reference Acer**. Owner physical result: black screen with a brief blinking cursor, then
black; no Greia boot screen, no installer, installation never startable. This is the first
physical evidence ever obtained for this artifact and it is **negative at the earliest
stage**. The stick is with the owner.

Flashed artifact (unchanged, still verifiable):
`out/physical-test-acer/greia-os-installer-acer-aspire-one-i386-ab.img`, 1818230784 bytes,
SHA-256 `f75b7c4f105420fbf11323062f5a50ba59c4516d66de48b9e3e09782b414f6d7`, built from
the verified S03 bundle `6b5cf05f…` at `b3bccfb4`. **Source-state correction:** the build
ran one documentation commit behind `main`. `git pull` had failed on credentials, so no
sync occurred and the checkout was the parent of `7d337d0d`; the owner's stated head
`7d337d0d` was correct. The missing commit touches only `HANDOVER.md` and the Orbiter disk
investigation, so no production source or build input was affected. This record was rebased
onto `7d337d0d`. **A failed `git pull` is not evidence a checkout is current** — verify
against `origin/main` before asserting a source state.

**Cause class is already documented and was not respected.** The proven reference path is
`legacy-x86-i686-dev` on Syslinux/FAT32; `build/live-syslinux/syslinux.cfg.in` states that
**GRUB's MBR does not work on that Acer firmware+stick combination**. The flashed image is
the GRUB path (`image_layout=bios-single-ext4`, only `i386-pc` modules, no ESP). It also
carries the diagnostic-suppression cluster that
`docs/reviews/2026-08-20_ACER_INSTALLER_BOOT_REGRESSION.md` §3.1/§3.2/§3.4 removed as
unaccepted — the live command line is `quiet splash loglevel=0 console=null panic=0`, which
discards all kernel output and reboots on panic, converting a diagnosable early failure
into exactly the reported blindness. `console=null` is still live in current source at
`build/build-installer-image.sh:490` and three other sites, and the removed
`build/overlay/boot/grub/greia-theme.txt` plus 1600x900 full-colour auto-regeneration were
reintroduced on 2026-08-20..24 and are in the shipped image.

**Two hypotheses were tested and refuted; do not re-propose them.** PAE is not the boot
cause: a four-way QEMU CPU cross-test (diagnostic image, no loop devices) showed
`core2duo`, `n270` and `qemu32` all boot the kernel and reach the live squashfs, with
`WARNING: PAE disabled` appearing in **zero** runs. UEFI-only firmware is a real support
limitation (the image is provably BIOS-only) but is not established as this failure. The
QEMU work does prove the GRUB→kernel→initramfs→squashfs chain is sound on emulated
legacy-BIOS x86.

**Separate real defect:** `build/write-image.sh:51` requires `lsblk --json <dev>` to return
exactly one entry, but util-linux 2.39.3 returns the disk plus partitions as flat siblings,
so the safe writer **cannot flash any already-partitioned USB stick**. Flashing required an
owner-authorised `sgdisk --zap-all` outside the writer before the writer would accept the
media. Do not repeat that silently.

**Mark the A/B GRUB route UNPROVEN on the reference Acer** until a positive physical result
exists; `docs/reviews/2026-08-20…` still records its re-acceptance as pending. Eight
decisions (D1–D8) are posed in the review, chief among them: which boot path is the
product path, and whether `console=null`/`panic=0` may ship in a product installer.

**Next exact step:** owner returns the stick, then
`sudo bash tools/build-and-flash-development-usb.sh legacy-x86-i686-dev /dev/sdX`,
requiring both installer-artifact and final read-only USB verification to report PASS
before booting, and recording the last visible boot stage per the 2026-08-20 review §8.
Do **not** rebuild or reflash `acer-aspire-one-i386-ab` onto the reference Acer until D1
and D2 are decided. Full report: `docs/reviews/2026-09-27_ACER_AB_GRUB_INSTALLER_PHYSICAL_BOOT_FAILURE.md`.

**Host residue:** two leaked Greia loops (`/dev/loop2`, `/dev/loop34`, both `autoclear=1`)
from the build runs; they clear only on reboot. Do not delete
`/tmp/greia-installer-build.iMc2gy/` before that reboot — its backing file is attached.
The build-host disk is the **replacement** drive serial `S2R7J9HB601552`, SMART `PASSED`,
zero error counters; the 2026-09-25 heavy-I/O prohibition no longer applies.


## 66. Acer physical boot: A/B GRUB USB route rejected on reference device (2026-09-27)

Physical test of the flashed `acer-aspire-one-i386-ab` raw GRUB/MBR installer failed at the first boot stage on the reference Acer: brief blinking cursor, then black screen; no Greia boot screen or installer. This result is consistent with the already accepted `docs/INSTALLATION_USB_BOOT_POSTMORTEM.md` and `docs/reviews/2026-08-20_ACER_INSTALLER_BOOT_REGRESSION.md`: this Acer + USB combination does not execute Greia's GRUB MBR path reliably, while the physically proven removable-media path is active FAT32 + Syslinux.

Do not use the A/B GRUB raw installer as the next Acer physical test. The A/B route is **UNPROVEN on the reference Acer** and currently has one negative physical result. The next Acer test must use the named `tools/build-and-flash-development-usb.sh legacy-x86-i686-dev <device>` procedure, which preserves visible tty1 diagnostics and the proven Syslinux/FAT32 first stage. Record the last visible boot stage.

The safe raw-image writer also had a separate util-linux compatibility bug: scoped `lsblk --json` can return a disk plus its partitions as flat siblings. `build/write-image.sh` now accepts only direct partition siblings of the confirmed target disk while preserving root-disk/removable/identity safety checks; manual partition-table zapping is no longer the intended workaround.

Do not infer that the A/B storage/update design itself is invalid from this USB first-stage failure. After the Syslinux physical sanity test, the product task is to reconcile the A/B installer medium with the proven Syslinux removable-media first stage rather than asking the Acer to boot the already-refuted GRUB/MBR USB path again.

## 67. Acer Syslinux dev USB built; read-only verifier FAT gate fails benignly (2026-09-27)

At HEAD `cadfe4721a34451a03d673176790c02fff1b2a72` the named proven Acer procedure was
run for real:

```bash
sudo bash tools/build-and-flash-development-usb.sh legacy-x86-i686-dev /dev/sdb
```

USB confirmed as `/dev/sdb`, LaCie iamaKey, serial `eca3505216d7d3`, 8086618112 B, `RM=1`,
after unmounting the desktop's `/media/orb/PIP_INSTALL` automount. The build
(`legacy-x86-i686-dev`, not the A/B GRUB engineering image) produced
`out/greia-os-installer-legacy-x86-i686-dev.img`, 1289748480 bytes, SHA-256
`5b8bada7797a363173303978461d0f583cb306c567f29934ec73455e1b214c91`, and reported
`Developer installer artifact verification: PASS`. The media was written with the
postmortem-proven writer: active FAT32 `GREIA` spanning the stick, Syslinux VBR patched
into the partition boot sector (`SYSLINUX` OEM + embedded `ldlinux.sys` path),
`/usr/lib/syslinux/mbr/mbr.bin` in the MBR first 440 bytes with the `0x55AA` signature,
and `ldlinux.sys` + `syslinux.cfg` + modules under `/boot/syslinux` via
`syslinux --install --directory /boot/syslinux`.

**The final read-only USB verification FAILED**, so the stick is **not** cleared for the
owner's Acer test yet. `tools/verify-live-usb.sh` runs `fsck.vfat -n "$USB_PART"` and
treats any non-zero exit as failure. The two reported conditions are benign for this recipe:

- `There are differences between boot sector and its backup. This is mostly harmless.`
  Cause is exact and expected: `syslinux --install` patches partition sector 0 (OEM becomes
  `SYSLINUX`, `ldlinux.sys` path embedded) and does **not** update the backup boot sector at
  sector 6, which still reads `mkfs.fat`. Verified by dumping both sectors.
- `Reclaimed 29 unused clusters (118784 bytes)` / `Free cluster summary wrong
  (1707929 vs. really 1707958)` — minor FAT accounting drift after the large file copies.

Every substantive check the gate never reached was then run independently and **all
passed**: partition 1 bootable; `.disk/live-uuid` match
(`667eed94-5e75-4ff1-ab59-46540e999c9b`); `console=tty1` present; `panic=0` present; no
`quiet`/`splash`/`console=null`/`loglevel=0`/timed-panic; `vmlinuz`, `initrd.img` and
`filesystem.squashfs` byte-identical to the image; all three `payload/` files
byte-identical; `boot/syslinux/syslinux.cfg` identical to the rendered template;
`ldlinux.sys` present. So the media is content-correct and bootable, and the failure is a
**verifier gate that is too strict for the proven writer recipe**, not a defective stick.
Owner decision required: accept the benign fsck condition, or narrow the gate to assert on
real FAT corruption. Do not simply delete the check.

**Safe-writer fix validated narrowly.** `d4bece31` (`build/write-image.sh`) is present;
`bash -n build/write-image.sh` passes. One narrow regression was added to the existing
owner `tests/test_greia_release.py` (`SafeMediaWriterTopologyTests`) pinning exactly the
corrected rule: a removable whole disk with its own direct `part` siblings passes the
topology gate, an unrelated mapper/lvm sibling is still refused. 14/14 pass in that module.

**Documentation reconciled.** `docs/architecture/UNIVERSAL_GREIA_SETUP_MEDIA_ARCHITECTURE.md`
was checked and is **already correct** about the legacy removable first stage
(`MBR -> active FAT32 -> SYSLINUX`) and already forbids replacing it with GRUB; only its
authority line lacked ADR 0036, now added. The runbook and handoff sections claiming that
document "still describes GRUB MBR" were false and are corrected by appended notes. §12 was
appended to the 2026-09-27 failure review stating the failed artifact was the
standalone/intermediate Session-04 GRUB engineering installer and that the
one-universal-image architecture is not invalidated.

**Stale loops: now three, and the build leaks one per run.** `/dev/loop2` (Acer A/B image,
live backing file), `/dev/loop34` and `/dev/loop35` (backing files already deleted). All are
`autoclear=1` with lingering partition mappings and clear **only on reboot**. This is
reproducible, not a one-off: `build/build-installer-image.sh` cleanup reports
`loop partition mappings remain after bounded partx teardown` on this host, and
`GREIA_AGENT_OPERATIONS.md` §12 requires `losetup -a | grep greia` to be empty after every
build, which is currently **not** satisfied. **One Orbiter reboot is owed.** Do not delete
`/tmp/greia-installer-build.iMc2gy/` before that reboot — `/dev/loop2` is still attached to
it. Do not use `losetup -D`.

Session 04 remains OPEN and untouched by this turn: no QEMU lifecycle leg was run, no
transaction/capability source was changed, and `CAP_CHOWN` remains **NOT AUTHORIZED**.

## 68. Built-in Activity Simulator, Audio, Readiness & Performance Audit (2026-10-01)

An exhaustive headless simulator and static audit was executed across all 41 first-party built-in activities (`activities/`):

1. **Supervisor Readiness & Lifecycle Stop Handling Defect Fixed:**
   - `activities/faccine_momo/momo_app.py`, `activities/mondo_contrari/contrari_app.py`, and `activities/quattro_stagioni/tree_app.py` were missing `mark_activity_ready()` and `activity_stop_requested()`. In production, `ActivitySupervisor` enforces a 15.0s `ready_deadline`, causing processes without `mark_activity_ready()` to be killed with `READY_TIMEOUT`.
   - Added `mark_activity_ready()` after the first frame flip and added `not activity_stop_requested()` to their main loop conditions.
   - Hardened `tests/test_first_party_activity_readiness.py`: removed the bypass skip so all 41 activities are strictly asserted to signal readiness. Test passes (1/1 in 0.264s).

2. **Spoken Audio Assets & Localization Completed:**
   - Audited launcher spoken titles and collection spoken labels via `tools/audit_launcher_spoken_labels.py`.
   - `activities/bosco_numeri` was missing `activity-title.wav` in Italian and English.
   - Generated canonical spoken audio using the Greia voice production pipeline (`tools/greia_voice.py`) with Tito character anchor (`tito-reference-v1.flac`) via Chatterbox MLX:
     - `activities/bosco_numeri/locales/it/audio/activity-title.wav` (+ receipt)
     - `activities/bosco_numeri/locales/en/audio/activity-title.wav` (+ receipt)
   - Registered audio bindings in `activities/bosco_numeri/locales/it.json` and `activities/bosco_numeri/locales/en.json`.
   - Created reproducible generation script `tools/generate_bosco_audio.py`.
   - `tools/audit_launcher_spoken_labels.py` confirmed 100% complete: `BUILT_IN_ACTIVITIES=41`, `ACTIVITY_TITLE_LOCALE_COMBINATIONS=82`, `ACTIVITY_TITLE_COMPLETE=82`, `COLLECTION_LABELS_COMPLETE=38`, `RESULT=PASS`.

3. **Performance & Idle Event-Driven Loops Clarified:**
   - 32 activities render continuously at ~60 FPS (or capped display rate).
   - 9 activities (`bottega_delle_misure`, `casa_del_dieci`, `festa_delle_rime`, `luci_di_momo`, `morbidi_mostriciattoli`, `nanna_delle_nuvolette`, `officina_dei_suoni`, `posta_di_leo`, `specchi_magici`) utilize dirty-flag / event-driven rendering (`if self._dirty: ... flip()`), registering 0.0 FPS when idle. This is intentional and compliant with low-resource appliance standards to conserve CPU and battery.

4. **Master Report Artifact:**
   - Full audit report generated in artifact `GREIA_ACTIVITIES_SIMULATOR_AND_STANDARDS_AUDIT_REPORT.md` (`file:///Users/taio84/.gemini/antigravity/brain/dfcc645e-cd1d-42cf-9eae-f56ebc4923c1/GREIA_ACTIVITIES_SIMULATOR_AND_STANDARDS_AUDIT_REPORT.md`).
   - Machine-readable raw benchmark data preserved in `scratch/full_activity_audit_results.json`.

5. **Verification:**
   - `python3 tools/audit_launcher_spoken_labels.py`: PASS (82/82).
   - `tests/test_first_party_activity_readiness.py`: PASS (41/41 verified).
   - `tests/test_activity_contract.py`: PASS (11/11).
   - Headless simulator verification: `org.greia.faccine-momo` and `org.greia.bosco-numeri` verified with clean Home return (`rc=0`).

## 69. Core Action & Strategy Game Archetypes Implemented (45 Activities Built-in, 2026-10-01)

Following the catalogue strategy analysis in `docs/product/ACTIVITY_CATALOGUE_AGES_3_5_STRATEGY.md` (Sections 7, 8, 9), implemented and verified four first-party built-in game activities providing intuitive physics, spatial reasoning, recoverable failure, and strategic turn-taking:

1. **`org.greia.corsa-bacche` ("La Corsa delle Bacche" / "Berry Chase"):**
   - Directory: `activities/corsa_bacche/`
   - Lead Mascot: Momo the squirrel (canonical audio anchor: `momo-reference-v1.flac`).
   - Archetype: Cute Maze Chase (action/nature/puzzles; motor reaction, spatial mapping, cognitive inhibition).
   - Features: Orchard hedge maze, berry harvesting, patrolling garden critters (Baffo the hedgehog, bees), Rainbow Star Berry invulnerability power-up causing critters to spin dizzily, and recoverable bump-back failure without harsh game-over.

2. **`org.greia.colline-allegre` ("Colline Allegre" / "Bumpy Hills"):**
   - Directory: `activities/colline_allegre/`
   - Lead Mascot: Tito the explorer bear (canonical audio anchor: `tito-reference-v1.flac`).
   - Archetype: Hill Vehicle Physics (action/nature; timing, momentum, motor coordination).
   - Features: 2D spring suspension physics over rolling green hills, wooden bridges, mid-air chassis tilt balance for smooth landings, collectible stars/gears/balloons, and a comical cartoon boxing-glove spring uprighting if flipped upside down.

3. **`org.greia.torre-forme` ("La Torre delle Forme" / "Shape Tower"):**
   - Directory: `activities/torre_forme/`
   - Lead Mascot: Lilli the builder cat (canonical audio anchor: `lilli-reference-v1.flac`).
   - Archetype: Spatial Stacking & Falling Shapes (building/puzzles; geometry, spatial composition, planning).
   - Features: Wooden block geometry inside a tower frame; 3 progressive developmental modes (*Costruisci Libero* static blueprint matching for age 3, *Scendi Piano* slow falling lines for age 4, *Sfida della Torre* classic child-paced puzzle with line clears and rainbow stars for age 5); positive celebration fireworks on reaching tower top.

4. **`org.greia.quattro-amici` ("Quattro Amici in Fila" / "Four Friends in a Row"):**
   - Directory: `activities/quattro_amici/`
   - Presenters: Flash the rabbit (carrot discs) vs Leo the owl (acorn discs) (canonical anchors: `flash-reference-v1.flac` and `leo-reference-v1.flac`).
   - Archetype: Turn-Taking Adversarial Strategy (puzzles; turn-taking, prediction, spatial planning).
   - Features: Slotted wooden drop board with realistic gravity/bounce; Solo vs Friendly CPU (*Contro Leo* with progressive AI) and local 2-Player Pass-and-Play (*Due Amici* on the same screen); Connect 3 on 5×4 grid (D1–D2) scaling to Connect 4 on 7×6 grid (D3–D4).

**Standards & Platform Verification:**
- **53 dedicated unit tests PASS**: `tests/test_activity_corsa_bacche.py` (10/10), `tests/test_activity_colline_allegre.py` (13/13), `tests/test_activity_torre_forme.py` (14/14), `tests/test_activity_quattro_amici.py` (16/16).
- **Spoken Audio Audit**: `tools/audit_launcher_spoken_labels.py` PASS (**90/90 combinations, 100%**).
- **Contract & Audience Audits**: `tests/test_activity_contract.py` PASS (11/11, 45 built-ins), `tests/test_first_party_activity_readiness.py` PASS (45/45 verified), `tests/test_first_party_activity_audience_metadata.py` PASS (3/3).
- **Architecture Audits**: `tools/audit_activity_backend_independence.py activities` PASS (45 activities, 0 blockers, 0 new migration findings), `tools/audit_activity_system_chrome_ownership.py --strict` PASS (0 blockers).


## 70. Acer installer/first-boot hardening reconciled onto canonical main; source acceptance owed (2026-10-03)

The previous review-candidate sequence exposed two process/architecture errors before another hardware cycle:

1. repository policy requires direct work on `main` unless the owner explicitly requests a branch; the review-branch pattern was inherited incorrectly and is no longer the continuation route;
2. wireless L3 ownership is **role-specific**, not globally owned by iwd or networkd.

Canonical source now expresses the paired role contracts:

- live installer: `EnableNetworkConfiguration=true` + wireless
  `[Link] Unmanaged=yes` — iwd owns association/authentication and L3;
- installed target: `EnableNetworkConfiguration=false` + wireless
  `[Network] DHCP=yes` — iwd owns association/authentication and networkd owns
  target DHCP/L3.

The regression test and both development artifact verifiers now validate the
`iwd/main.conf` policy together with the matching wireless networkd policy, so
both "two DHCP owners" and "no DHCP owner" states are rejected.

The same canonical tranche includes the reviewed bounded B4 profile-data
migration from the Acer restart-loop investigation: the fixed profile-data root
is normalized cheaply every boot, existing profile roots are repaired once for
shared group-write, only existing child-owned `storage`/`progress` subtrees
are recursively re-owned, and symlink/non-directory data roots fail closed.

**Evidence boundary:** SOURCE ONLY / UNPROVEN. No image has been rebuilt from
this reconciled `main`, no USB has been flashed, and the Acer has not been
modified. Previous V4 local acceptance intentionally stopped at the contradictory
installer Wi-Fi policy and did not execute later test gates.

**Next exact step:** local source acceptance on the exact current `main` SHA.
Do not build, flash, install, merge, or touch the Acer until that source gate is
reviewed.

## 71. Source acceptance found one stale B3 staging test; corrected, rerun owed (2026-10-03)

Source acceptance of `af6fb79298e7b6ed5366151aa14ebe2e3d26ebd1`
passed the role-specific Wi-Fi matrix, contradiction search, shell syntax,
85/85 focused tests, both Wi-Fi negative controls and all ten B4 migration
properties. Full `make verify` stopped with 16 failures: exactly the historical
15 unrelated failures plus one new stale assertion in
`tests/test_image_staging_contract.py::TargetImageCarriesFirstBootFixesTests::test_first_boot_repairs_profile_data_ownership`.

The stale test still required the retired B3 marker and recurring/unbounded
ownership repair. Canonical `main` now changes only that test, replacing it
with image-staging assertions for the accepted bounded B4 contract:

- refuse symlink and non-directory profile-data roots;
- normalize the fixed data root to `greiakid:pipprofiles` mode 2770 every boot;
- use the `b4-profile-child-roots-v1.done` marker for the compatibility pass;
- repair top-level profile roots to shared group-write;
- recursively re-own only `progress` and `storage`;
- use `-xdev` and `chown -h`;
- reject return of the retired B3 marker, 2755/0777 modes or whole-data-tree
  recursive ownership sweep.

No runtime implementation changed in this correction and no verification has
yet executed against the new HEAD. **Next exact step:** run the corrected
staging-contract suite, the previously focused first-boot/profile suites, then
`make verify` on the exact current canonical `main`. Do not build, flash or
touch the Acer until that evidence is reviewed.

## 72. B4/network reconciliation source gate accepted; tail source gates remain (2026-10-05)

Exact tested source: `69624a4f96d6f441327966a85ba5deb0ea3fcab4`.

The corrected staging suite passed 19/19. The five focused suites passed 85/85.
Both negative controls rejected the intended bad states. Full unittest discovery
ran 3897 tests with exactly the established 15 unrelated historical failures and
8 skips; the one previously new B4 staging failure disappeared, and the failure
identity set matched the historical baseline exactly. The checkout remained
clean; no build, flash or Acer operation occurred.

**Disposition:** the B4 profile migration + role-specific Wi-Fi ownership
reconciliation is **SOURCE-ACCEPTED**.

`make verify` still exits during its test prerequisite because the historical
15 are unresolved, so `validate`, `shell-check` and `footprint` were not
reached. The canonical development build+flash front door does not call
`make verify`, but we will not spend a destructive hardware cycle until those
three source gates execute explicitly and the build host passes the mandatory
disk-health/loop preflight.

**Next exact step:** non-destructive local pre-build acceptance on canonical
`main`: explicit project/activity validation, executable-shell syntax gate,
source-footprint gate, then SMART/kernel-error/disk-usage/loop audit. Do not
build or flash in that run.

## 73. Pre-build validation found two unnecessary forbidden Activity imports; fixed, re-validation owed (2026-10-05)

The non-destructive pre-build gate stopped at `make validate` on canonical
`bd6af6438a7345aa30c9b663c45a14e82a7ccb2d` because two newly added
Activities imported `sys`, outside the curated child Python runtime.

Canonical `main` now removes those unnecessary dependencies without widening
`runtime/child-runtime.toml`:

- `colline_allegre/main.py`: removed manual `sys.path` mutation and the
  now-unused `pathlib.Path`; direct script execution already receives the
  Activity directory on Python's import path and Greia launches with the
  Activity root as cwd.
- `corsa_bacche/main.py`: replaced `sys.exit(main())` with
  `raise SystemExit(main())`.

A new global regression validates every bundled Python Activity against
`PythonRuntimeAdapter(policy=PythonRuntimePolicy.load(child-runtime.toml))`,
so future Activity-specific unit suites cannot silently bypass the curated
runtime-import contract.

**Evidence boundary:** source edited, not yet locally executed at this new HEAD.
Next exact step is to rerun the new runtime-policy regression and `make
validate`; if green, continue the previously blocked `shell-check`,
`footprint`, bytecode-cleanliness and build-host health/loop preflight. Do not
build or flash before that pre-build gate is green.

## 74. Partition-scanned loop leak root-caused and repaired at source; synthetic host acceptance next (2026-10-06)

The non-destructive pre-build gate was source-green but stopped on a pre-existing
`/dev/loop11` mapped to a deleted
`greia-installer-build.../target-out/greia-os-legacy-x86-i686-dev.img`.

Root cause is now explicit: `build/build-installer-image.sh` created the
target payload loop with `--partscan`, later used plain `losetup -d`, and
cleared `TARGET_LOOP` immediately. A surviving partition child could leave the
parent AUTOCLEAR loop associated; final cleanup had forgotten it and deleted the
backing tree.

Canonical source now requires shared verified loop teardown in the installer
builder, legacy finalizer, development-installer verifier and live-USB
readback verifier. A loop variable is cleared only after
`safe_detach_loop` verifies both partition-child removal and parent
disassociation. Cleanup failure fails closed and preserves work data.
`tests/test_build_loop_cleanup_contract.py` enforces the rule across every
build/tool shell script that creates a partition-scanned loop.

**Evidence boundary:** SOURCE EDITED / UNVERIFIED locally at the new HEAD.
The existing historical `/dev/loop11` is still a host-state blocker and was
not touched by this source work.

**Next exact step:** run focused source/shell checks plus a disposable synthetic
`--partscan` loop using the shared helper on the build host. Do not run a full
image build. If the synthetic lifecycle passes, reboot or otherwise safely
clear the pre-existing historical loop, re-prove the loop audit is empty, then
resume the canonical development build+flash gate.

## 75. Final two unsafe partscan owners fixed; loop-contract rerun is the only remaining pre-build source gate (2026-10-06)

After host reboot, all stale Greia loops were gone and a disposable
`--partscan` ext4 probe proved `safe_detach_loop` removes both partition
children and the parent loop association without residue.

The new repository-wide regression then found two remaining direct-detach
paths: `tools/build-live-usb.sh` and
`tools/verify-development-target-image.sh`. Both are now migrated to the
shared verified cleanup primitive. The Syslinux/FAT32 writer's destructive
media recipe is unchanged; only lifecycle cleanup of its read-only installer
image loop changed.

**Current evidence:** source patch committed; local rerun of the loop-contract
test and focused shell/source gates still owed at the new HEAD.

**Next exact step:** run the loop cleanup regression, syntax/source gates, and
confirm the post-reboot host still has zero Greia loops. If green, the
pre-build gate is finally closed and the next run may use the canonical
`tools/build-and-flash-development-usb.sh legacy-x86-i686-dev <LaCie device>`
front door, after re-identifying the LaCie by serial and unmounting it.

## 76. Final pre-build PASS; next step is the real build/flash/Acer campaign (2026-10-06)

Exact tested source: `8eec98d7b5e52375bf08790f2fd00cf8a5f006d0`.

The last remaining source blocker is closed. The loop-cleanup contract passed
3/3, all seven partition-scanned loop owners use the shared verified lifecycle,
project validation passed all 45 Activities, shell syntax and footprint passed,
and the post-reboot build host has zero Greia loops with root usage below 80%.
A disposable real `--partscan` + ext4 mount/write/unmount probe independently
proved that `safe_detach_loop` removes both the partition child and parent
association. The LaCie iamaKey was identified by serial
`eca3505216d7d3` as a removable whole disk and was intentionally left mounted
and unwritten during the pre-build gate.

**Disposition:** FINAL PREBUILD PASS. Do not insert another source-only gate.

**Next exact step:** re-identify the LaCie by serial, unmount all of its mounted
filesystems, and run the canonical development front door:
`sudo bash tools/build-and-flash-development-usb.sh legacy-x86-i686-dev <device>`.
Require both source artifact verification and USB readback verification, then
audit for zero Greia loops. Only after that move to the Acer: boot the proven
Syslinux/FAT32 medium, perform a fresh install, remove the USB, and judge the
first installed boot with no hotpatch and no second corrective boot.

## 77. Build/flash artifact PASS, loop-hygiene FAIL; Acer was correctly not started (2026-10-06)

A full canonical `legacy-x86-i686-dev` build+flash at
`64103e48412b6ccafbd8c68b1585f7dc3e7ff2ef` produced and readback-verified
the LaCie successfully:

- image SHA-256
  `f803c9edff7482b122dea49abd7d12e664d7773dc9ef3180cffb45c4387d801d`;
- `source_artifact_verification=PASS`;
- `usb_flash_readback_verification=PASS`;
- Syslinux/FAT32 writer unchanged and PASS;
- live media id `2afcbbba-9722-4020-8caf-a16132b54f51`.

The run then stopped at the mandatory loop audit. `/dev/loop0` remained bound
to the deleted target image with `loop0p1` present. Acer USB boot, live Wi-Fi,
install and first installed boot were **not** attempted.

Root cause was not simply a missing call: the first cleanup redesign had the
wrong lifecycle order for this kernel. It tried `partx -d` until children
vanished before ever requesting parent detach. The child does not vanish in
that state. Source now requests lazy parent detach after unmount and waits until
both parent association and children disappear, while pinning backing identity
against loop-number reuse.

Two additional defects are repaired: non-mount paths no longer let
`findmnt --target` walk the containing root filesystem, and EXIT-trap cleanup
failure now exits the process non-zero through shared `safe_cleanup_exit`.
The canonical build+flash front door itself now treats residual Greia loops as
a success-condition failure.

**Next exact step:** local source tests plus one tightly scoped application of
the new helper to the existing leaked Greia loop, after proving its backing
identity and unmounted state. If that exact field reproduction clears and the
checkout gates are green, no target/runtime bytes changed since the already
verified USB was produced; the owner can decide to proceed directly with that
USB to Acer rather than spend another full build solely to regenerate identical
product payload bytes.

### Loop cleanup redesign candidate

Implementation candidate:
`258f2189a6e2e9de604becd8b63b4eab28771113`.

This candidate includes the lazy-detach ordering, backing-identity pin,
non-mount short-circuit, authoritative EXIT-trap status propagation, all seven
partscan owners, the canonical front-door pre/post loop gate, and executable
regressions. Local acceptance is still owed. Documentation-only descendants are
acceptable only after proving their diff contains no build/tool/test/runtime
implementation.

## 78. Exact leaked loop defeated parent-only detach; third-generation interleaved cleanup ready for field acceptance (2026-10-06)

The existing `OPrdqB` `/dev/loop0` was safely identified and tested once
against the parent-first helper. It remained associated with deleted backing
and `loop0p1`; AUTOCLEAR became 1 but teardown never completed. No retry,
manual partx, detach-all, reboot or Acer action followed.

Source now implements the missing combined sequence: parent detach first,
then bounded `partx -d` only if children remain while teardown is pending,
then settle/recheck until both parent association and children are gone.
Backing identity is pinned and failures print opener/holder diagnostics.
A real privileged deleted-backing fixture now reproduces a held partition
opener instead of only testing clean loops.

**Next exact step:** source/shell tests, then run the privileged deleted-backing
fixture, then apply the new helper once to the still-existing exact OPrdqB loop.
If that clears, reverify the existing installer image and already-written
LaCie; do not rebuild product bytes merely for cleanup validation.

### Interleaved cleanup implementation candidate

Exact implementation candidate:
`3f3f50d1f586872c6b02865e027635b3ac67c1fb`.

This includes the post-detach `partx` fallback, opener diagnostics, restored
partx dependency declarations across all seven owners, deterministic ordering
regressions, and the privileged deleted-backing field fixture.

## 79. Interleaved acceptance stopped on stale PARTSCAN_OWNERS pin; one-line test repair landed (2026-10-07)

The field-acceptance run at `6b3706d4` reached the focused test suite and
stopped with 10/11 PASS. The only failure was the global partscan-owner
inventory: the newly added deleted-backing fixture creates a `--partscan`
loop and correctly uses the shared cleanup helper, but was omitted from the
hard-pinned owner tuple.

Repair commit:
`6de59fba28a889cc86550926f0bca870eb01ed27`.

The repair adds `DELETED_BACKING_FIXTURE` to `PARTSCAN_OWNERS` and changes
nothing else. Resume local acceptance from the focused suite; all real loop,
artifact, USB and Acer evidence remains exactly as previously recorded.

## 80. Stop loop teardown redesign; historical OPrdqB loop requires reboot but does not block Acer acceptance (2026-10-07)

The exact OPrdqB orphan defeated all three bounded cleanup orderings, while the
current helper passes both fresh partscan teardown and the privileged
deleted-backing/held-partition fixture. The field loop has no mounts, no
userspace openers and no sysfs holders, remains AUTOCLEAR, and is now treated as
historical poisoned kernel state.

Do **not** add another removal primitive for this one stale loop. Reboot is the
supported way to clear it before any future build.

Important routing change:

- new build/flash: still requires zero pre-existing Greia loops;
- verifier/read-only checks: may use baseline-aware accounting and must create
  zero **new** Greia loops;
- existing LaCie Acer acceptance: may proceed without rebuilding and without
  clearing the historical host loop first, because product content has not
  changed since the verified USB was written.

Next: existing image digest + baseline-aware artifact/readback verification,
then physical Acer boot/install/first-boot acceptance.

## 81. Fresh Acer first boot loop fully root-caused; source fixes landed, new image required (2026-10-07)

Physical read-only diagnosis of the fresh install proved the child shell dies
creating `<profile>/progress`: the Parent-created profile root was
`greiapanel:pipprofiles 2750`, while the data root was correctly
`greiakid:pipprofiles 2770`. B4 had completed 17 seconds before the Parent
created the profile, so the old prevention repaired the container but not the
creation mechanism.

The deeper source contradiction was `RestrictSUIDSGID=yes` plus a
`chmod(2770)` repair whose `PermissionError` was silently swallowed.
Current source keeps the hardening, adds Parent `UMask=0007`, verifies exact
mode/group, and refuses to publish a profile until its shared directory
contract exists. B5 repairs already-existing bad Parent-owned shared
directories on upgrade.

The same field capture found two independent defects:
- the A/B boot observer was enabled on `bios-single-ext4` and failed namespace
  setup because its A/B identity files cannot exist there; composition is now
  storage-layout aware;
- `greia-devctl status/logs` unnecessarily required a missing display
  descriptor, and canonical target composition never provisioned that file.
  Status/logs are now display-independent and canonical developer composition
  writes the role-specific descriptor; screenshots remain fail-closed.

The `pkexec` warning remains open/non-blocking.

**Evidence:** source edited and regression coverage added, but no owner/local
tests have run at the new HEAD yet.

**Critical routing:** the old verified LaCie predates these product-content
changes. Do not use it to accept the fix. After source acceptance, reboot the
build host (required to clear historical OPrdqB poisoned loop), require zero
Greia loops, then perform a new canonical build+flash and repeat fresh Acer
installation/first-boot acceptance.

### Fresh first-boot repair candidate

Exact implementation/test candidate:
`af97ddbd7a881d3977c83c1ee99da1b8c0e7e997`.

Everything after this candidate in the current documentation update is
documentation-only. Local/owner source acceptance has not yet run.


## 82. Creations interoperability + all-Activity release program started, platform core SOURCE-WIP (2026-10-07)

### One durable product/content continuation path

Owner explicitly approved and requested a comprehensive **single implementation
plan** covering typed shared child creations, one universal pre-reader large-card
image/audio/text picker and gallery/viewer with deletion, cross-Activity creative
round trips, scaled disk budgets, a curated release set, and a deep quality
review/repair/test pass for **all 45** first-party Activities.

Read, in this order, when continuing this **content/product workstream**:

1. `AGENTS.md` (new explicit scoped-program pointer; existing lifecycle priorities preserved);
2. `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md` — single detailed plan, P0–P8, full 45-item review roster;
3. `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PROGRESS.md` — current exact status, dated evidence, next step;
4. `docs/product/CHILD_CREATIONS_LIBRARY_AND_MEDIA_INTEROPERABILITY.md` — accepted child-facing large visual thumbnails, audio-preview-before-pick, viewer/delete and privacy requirements;
5. existing live architecture and lifecycle plans / skills for relevant real code changes.

This content plan **does not replace** the 2026-09-15 fresh installation,
first-boot and update/rollback acceptance route, which remains OPEN. No new
installer or Acer acceptance was executed here; existing Acer image/source
evidence remains pinned to its own exact SHA.

### Actual source changes committed to main

**Trusted platform P1 core (not installed/connected):**

- `src/greia_platform/creation_capacity.py` — `CreationCapacityPolicy`
  defaults to 75% maximum occupancy of the actual writable data volume,
  with an independent 512 MiB free reserve; measured-space injectable probe.
- `src/greia_platform/creation_media.py` — bounded codec registry for
  normalized static PNG (384×320 max-size thumbnail), PCM WAV (playable source
  preview), UTF-8 text (bounded preview), independent of extension claims.
- `src/greia_platform/creations.py` — one-profile **trusted-only**
  `CreationLibrary`: immutable snapshot IDs, SQLite v1 index, stable
  descriptors with producer/type/role/integrity, bounded page listing,
  content read/digest check, polymorphic preview, explicit deletion.
- `tests/test_creation_library.py` — focused headless tests for the
  8-GiB→6-GiB occupancy example, small-volume safeguard, PNG thumbnails,
  WAV playback payload, UTF-8, independent profile roots, immutable
  revisions, valid delete, fail-closed malformed types, symlink paths,
  content tampering and quota refusal.

Commits include `c829825a`, `f41b4d2e`, `c27a6ce6`, `f278cbaa`,
`43d41532`, `bc28fc55`. The P1 repository is **not currently reachable
from an Activity sandbox**, not part of the Activity SDK, not a trusted
selection-token broker, and has no GUI, app integration or backup support.
Do not mount its directory into an Activity. The scoped producer/consumer
permissions and profile binding must be provided by the existing supervisor
authority and broker, not caller-authored strings/environment.

**Source-only Activity release triage:**

- `activities/colline_allegre/colline_app.py`,
  `colline_model.py` and `colline_renderer.py` now handle top-level
  script imports as well as package imports. `colline_content.py` no longer
  contains the dead conditional `auto_upright=false if False else False`.
- `tests/test_activity_colline_allegre.py` now tests script entrypoint
  import semantics via `runpy.run_path`; it does *not* execute the game loop.
- `activities/quattro_amici/activity.toml` now declares D1–D4 rather
  than nonexistent D5; `tests/test_activity_quattro_amici.py` checks
  manifest bounds against `LEVEL_CONFIGS`.
- Commits: `02b8f2e4`, `ee917b42` (intermediate immediately corrected),
  `1c8a45ee`, `faabb503`, `82ff2d23`, `7c444493`,
  `93bf54e1`, `35cb977f`. No claims of completed per-game release
  review or visual acceptance.

### Executed evidence and limits

Local environment had Python, Pillow and SQLite but **no local Greia checkout,
no Pygame, no complete Simulator or target GUI/display**. An isolated
mirror of the four new source files ran:

```bash
PYTHONPATH=src python -Werror::ResourceWarning -m unittest discover -s tests -p test_creation_library.py -v
# 12 tests: PASS, in the isolated copied/mirrored source
python -m compileall -q src tests
# PASS, in the isolated copied/mirrored source
```

This is **isolated SOURCE evidence**, not `make verify`, not a fresh
`main` checkout test, not source/image/package acceptance and not physical
Acer. The new Colline and Quattro tests have not executed at current head.

### Exact next tasks

1. On a complete local checkout of current `main`, run
   `PYTHONPATH=src python3 -m unittest discover -s tests -p test_creation_library.py -v`,
   `tests/test_activity_colline_allegre.py`, and
   `tests/test_activity_quattro_amici.py` plus standard `make verify`.
   Repair any concrete source failures in the owning code and update the
   progress ledger. The current shell/source tests must not be reported as
   hardware evidence.
2. Review P1 DB crash recovery, media resource bounds and schema handling
   with the real per-profile layout; ensure all profile data writers eventually
   share the disk-growth guard rather than letting another storage API fill
   the PERSIST volume.
3. Implement P2 session-bound access through the **existing** trusted broker
   and manifest/SDK semantics, proving negative cross-profile/handle-forgery
   tests *before* exposing reads/publishing to untrusted Activities.
4. P3 universal picker/viewer, P4 Painting↔Shape Garden↔Theatre PNG
   interoperability, P5 audio/text, P6 explicit release profile, P7 complete
   all-Activity QA and P8 actual hardware evidence, as ordered in the plan.
5. For any **real hardware** acceptance need, provide the owner exactly **one**
   fully self-contained local-agent instruction block with pinned SHA,
   non-destructive prerequisites, exact commands and required evidence,
   honoring the existing installer/first-boot route. No such hardware test was
   needed or requested during this source-only tranche.

**Risk:** Do not mistake a safe repository prototype for user-visible shared
files. No child can yet select an image from another Activity; the universal
picker/player/gallery and corresponding security semantics still need to be
built and visually evaluated.


## 83. Unified Creations + Activity Release — P2 trusted exchange source WIP (2026-10-07)

This is a subordinate **product/content** workstream; do not confuse its
source progress with closure of the independent Acer first-installed-boot and
multiplatform installer/update plan. Current resume is:
`docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md`
plus the sibling **`PROGRESS.md`**; `AGENTS.md` points there.

### Code landed on current main

- Manifest compatibility declarations: `[creations]` with `produces`
  and `consumes` typed PNG/WAV/UTF-8 sets are optional and parsed/validated
  in `src/greia_platform/activities.py`; preserved by the trusted
  `activity_index.py` serializer/reconstruction. Non-declaring Activities
  remain unaffected. Media declarations **are not direct library permission**.
- `src/greia_platform/creation_access.py` owns one Activity session's
  private-file-to-immutable-snapshot publication and one-use expiring
  selection grants; only the trusted Shell can issue child-selected
  handles, never an Activity RPC. Its producer ID comes from the trusted
  manifest/authority and private storage must match.
- `src/greia_launcher/storage_broker.py` adds exactly two new
  child-callable operations (`creations.publish_private`,
  `creations.import_selected`) on the existing per-session Unix socket.
  No operation permits child-side listing, deletion, arbitrary-ID reads,
  or minting a selection ticket. The broker's original start signature
  remains unchanged and the access owner is bound once before launch;
  handles are revoked on shutdown.
- `src/greia_launcher/supervisor.py` provisions the capability only
  if trusted launch manifests declare media types. It binds an
  `ActivityAuthority` with the current private storage under the
  active child's `ProfileContext.creations_dir`. Failure after opening
  a broker now cleans its socket/thread, rather than leaking resources.
- `src/greia_platform/creation_client.py` is the thin transfer SDK,
  `src/greia_platform/activity_api.py` provides `get_creations()`
  without an unsafe standalone fallthrough, and
  `ActivityStorageClient.creation_exchange` preserves transport encapsulation.
- `CreationLibrary` now preserves managed-group access for future
  child-data backup/restore, without opening the directory to Activity
  sandboxes.
- Regression sources: `tests/test_creation_access.py` (6 tests),
  `tests/test_creation_library.py` (12 tests),
  `tests/test_creation_broker.py` (3 new *unexecuted* real-socket tests),
  `tests/test_creation_manifest.py` (4 new *unexecuted* index/manifest tests).

### Executed versus owed evidence

The isolated local mirror under `/mnt/data/greia_session` contains the
Creations core, session-authority and two pure test files. Executed:

```bash
cd /mnt/data/greia_session
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -Werror::ResourceWarning -m unittest discover -s tests -p 'test_creation_*.py' -v
# 18 tests PASS on isolated mirror
```

AST parsing of the 4 mirrored source modules also PASSED. **The code and
tests for the real socket, indexed manifests, supervisor, existing full
storage and all Activities were NOT executed here**, because the local
container lacks an authenticated full Greia checkout and Pygame. There are
no screenshot, Simulator, installed target, full `make verify`, or
new Acer results. The new source is **not release-accepted**.

**IMPORTANT:** No built-in Activity yet declares `[creations]`, so the new
opt-in broker is dormant and a child cannot yet open the shared library
or export through a real Activity. There is no universal picker, playable
audio-preview UI, gallery viewer, child delete interaction, or cross-app
PNG/WAV/text integration yet. These are deliberate next phases, not
silently complete.

### Next exact step

1. In a **complete Greia checkout** at the then-current clean `main`,
   run the 4 `test_creation_*.py` suites, the relevant existing
   `test_activity_index.py`, `test_supervisor.py`, storage and profile
   suites; perform `make verify` before declaring P2 source acceptance.
   Fix any concrete failures in their actual owners.
2. Implement the **trusted platform-owned picker/viewer** P3 with beautiful
   large image cards, Play/Pause/Replay of selected WAV **before choose**,
   typed text cards, child-safe confirmation/delete and no filename
   dependency. This must preserve higher-trust Home/Back and input
   guarantees.
3. After a real child choice UI issues session handles, activate `[creations]`
   declarations in Painting and implement full Painting↔Shape Garden↔Teatrino
   immutable PNG round trip. Then voice/audio and text.
4. Implement and verify adaptive disk reservation for *all* profile writers,
   bounded recovery and logical backup/restore; review every existing
   Activity and explicit release composition as the unified plan requires.
5. Do **not** request physical install/flash or repurpose current Acer image
   to validate these source edits; the lifecycle owner must first complete
   fresh-boot acceptance. When real hardware is required, give one complete
   pinned, non-destructive local-agent instruction block as agreed.

Actual commits include `e59736b9`, `2ba77eb0`, `1e8bacaf`,
`f94b541e`, `5c9e0d82`, `c4676185`, `c4f15453`,
`c0e53230`, `e119b745`, `8588b656`, `a28e6be5`,
`b8d3007d`, `7050968a`, `e991706b`; the full
ordered change ledger is on GitHub and progress document.


## 84. Creations P3 Gallery / Painting publisher SOURCE-WIP — requires desktop visual acceptance (2026-10-07)

**Current owner-authorized release program:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md` and **living exact state** `PROGRESS.md`. The `AGENTS.md` task router already links them. This project remains subordinate to the **separate** unfinished Acer first-install/boot, architecture-remediation and update/rollback release lifecycle paths. No release or physical acceptance is claimed.

### Exact newly landed source candidate

**Pinned code/test source SHA:** `d63b9f530e684819e80e9e5a271c13bd953cc001`. Later plan/test/progress/HANDOVER updates are documentation-only. The complete changes are visible in GitHub history; this is not a claim of a local full Greia checkout.

**Reusable trusted child browser** (Gallery mode + Picker mode share one controller/renderer):

- `src/greia_platform/creation_gallery.py` — bounded indexed, profile-owned `ALL/IMAGE/AUDIO/TEXT` pages, visible-item/typed scope, focused cards, expanded image, audio play/pause/resume/replay only on explicit request, proper teardown, explicit viewer-only confirmation/delete, and picker-only opaque token after child chooses. An **explicitly empty** requested media set now fails closed (`89074d19`) instead of becoming unrestricted all-types.
- `src/greia_platform/creation_gallery_layout.py` and `creation_gallery_painter.py` — responsive big cards (two large pictures across reference 1024×600), system-chrome-safe title/tabs, real PNG thumbnails and original in detail, non-reader-friendly illustrated empty state, paper/text preview, vector audio/icon/touch targets and confirmation modal. No desktop file dialog, raw path or tiny filename grid.
- `src/greia_platform/creation_gallery_screen.py` — shared Greia `Screen` input/controller lifecycle, mouse and keyboard navigation, safe cancellation.
- `src/greia_platform/creation_audio_pygame.py` — actual on-demand SDL WAV channel, distinct Play/Pause/Resume/Replay, paused progress freeze, cleanup on exit/error. `src/greia_launcher/presentation.py` requests animation frames only during active audio playback.
- `src/greia_launcher/child_shell.py` and `catalogue_view.py` — the profile's **My Creations** destination is a real platform-owned Home portal, not an Activity. The Shell owns viewer, storage root, audio stop on logout/profile change, and Home return.
- `src/greia_platform/creations.py` filters mixed types in bounded SQL instead of scanning all items in Python.

**First producer: Painting → My Creations**

- `activities/painting/activity.toml` declares `[creations] produces = ["image/png"]`.
- `painting_renderer.py` adds a responsive kid-visible share-picture-up-arrow control. `painting_app.py` only publishes on deliberate action, saves private autosave/draft first, calls the trusted `get_creations()` broker SDK, reports success/failure and avoids duplicate publication of unchanged saved PNG in the same session. `painting_model.py` validates source private file name and `main.py` passes the optional SDK; standalone mode never mounts a shared folder.
- **Not yet supported:** browse/import shared images **from within Painting**; Shape Garden/Teatrino importing the image; WAV recording producer; shared UTF-8 producer. These remain P3/P4/P5 work.

**Source/test commits** include `f21b2830`, `263afbf5`, `946a2959`, `9392e94e`, `03e51e25`, `0ece3e64`, `041847d9`, `d95a7914`, `6e78b145`, `c77cf6ce`, `cb3345b4`, `ca9dc87d`, `89074d19`, `6595621a`, `d63b9f53`; see Progress for full explanations.

### Evidence honestly available

Assistant's **isolated** Python environment has Pillow + SQLite and no `pygame`, full private checkout or working Greia Simulator. A non-privileged pip attempt to obtain pygame-ce failed due DNS/network restrictions; **no GUI screenshots** could be rendered here. The local mirror of the pure repository/access/gallery/geometry and mocked audio owner tests was run on 2026-10-07:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/mnt/data/greia_session/src \\
  python -Werror::ResourceWarning -m unittest discover \\
  -s /mnt/data/greia_session/tests -p 'test_creation_*.py' -q
# 33 tests PASS — isolated mirror only
```

**Not run in complete repo:** Pygame Gallery/Screen/visual tests, `test_creation_broker.py`, `test_creation_manifest.py`, `test_painting_creations.py`, `test_activity_index.py`, `test_supervisor.py`, `make verify`, live save/reopen/delete flow. No physical Acer, install/build/update or performance evidence from these edits.

### Crucial real architectural issue for P3 picker

`LauncherApplication._launch_selected()` waits in an Activity supervisor poll loop while the **Activity owns the visible display**. Therefore a trusted browser rendered as a normal Home Screen cannot be assumed to overlay an active consumer Activity. The controller's `on_pick` callback and SessionAccess grant issuance exist, but **no real Activity→Shell request/response/display handoff exists yet**. This blocks actual in-Activity picker invocation. The master PLAN's P3 section now requires a properly designed request ID, cancel/timeout, Shell/Supervisor authority, backend-appropriate trusted overlay/display transition, restoration of focus/game clock/audio, and same-session returned handle. Do not hack it by letting consumer apps browse shared storage or by drawing Shell pixels behind a live Activity.

### Exact next action (not hardware)

A **single coherent desktop local-agent acceptance procedure** was committed at:

`docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md`

It pins source candidate `d63b9f53...`, instructs pristine ff-only `main` checkout and full focused + `make verify` tests, and requires unmodified real-Simulator screenshots for Home portal, empty/gallery, Painting explicit PNG share, gallery original zoom, cancel/confirm/delete, reference 1024×600 + 800×480 + 1366×768 and keyboard navigation. It forbids any Acer flash/install/device changes. STOP on first true failure; return evidence ZIP and report so next code tranche can repair actual owners rather than perform speculative patching.

**Implementation after desktop evidence:** fix discovered test/UX/runtime errors; deliver one authoritative trusted in-Activity picker mediation path; implement Painting↔Shape Garden↔Theatre PNG round trip; then voice and text; integrate 75% + reserve into **all profile-writing services**, logical backup, release catalogue curation and 45-Activity QA. All release stages remain open.


## 85. Creations P3 asynchronous picker transport and Painting image receiver — SOURCE-WIP; all tests deferred (2026-10-07)

**Current unified workstream:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md`; exact P1–P8 status and dated commit notes in sibling **`PROGRESS.md`**. `AGENTS.md` routes owner-authorized Creations work there. This product tranche **does not** clear the independent Acer first-boot/install/update lifecycle.

**Pinned source commit for later tests:** `1904e74921b62b78181f45206f394a6b6bf40dd6`. Later commits are plans/test instructions/progress/handover only.

### Source implemented (not release-accepted)

1. **Activity→broker→trusted Supervisor picker transaction** — new `src/greia_launcher/creation_selection.py`: single pending nonblocking typed `SelectionRequest`, random opaque ID, media subset and optional semantic-role filter, poll/cancel, absolute 180-second request timeout, 30-second terminal-result retention, close, stale-ID denial, and host-owned completion. `CreationSessionAccess` confirms MIME/role scopes at grant issuance; one-use import handle still cannot be minted by Activity.
2. **Transport + SDK** — existing `storage_broker.py` supports only three additional child operations (`creations.request_selection`, `creations.poll_selection`, `creations.cancel_selection`); `storage_client.py` and `creation_client.py` expose matching typed nonblocking APIs. No activity-directed listing, deletion, arbitrary creation IDs, grant minting or presenter-enable RPC exists. `ActivitySupervisor` exposes pending/complete/cancel through exact currently-RUNNING session broker.
3. **Crucial fail-closed availability gate** — picker requests are rejected immediately unless the **trusted display owner** calls `ActivityStorageBroker.enable_creation_picker()`; it is never activated by production Shell code yet. The system therefore does not start an invisible forever-pending child chooser while true in-Activity modal presentation is unimplemented. Tests can enable a simulated trusted presenter only within controlled host-side fixtures.
4. **Large-gallery role filtering** — `CreationLibrary.list` provides parameterized bounded SQLite MIME+semantic-role filtering with supporting indexes; the shared Gallery controller honors both to hide unrelated creations. No cross-profile source root exposed to Activity.
5. **Painting import prepared** — `activities/painting/activity.toml` declares `produces` and `consumes` `image/png`; `PaintingApp.accept_selected_png(handle)` reads only one platform-issued selection, checks payload integrity and format, decodes before changing state, saves a new **private** editable picture and preserves prior work on validation failure. This method is *not yet triggered by a child-visible chooser*. Existing deliberate share/auto-save behavior is unchanged.
6. **Regression sources added/expanded** — `tests/test_creation_selection.py`, `tests/test_creation_broker.py`, `tests/test_creation_gallery.py`, `tests/test_painting_creations.py` cover request state/expiry/cancellation, presenter missing/activated, real socket selection and one-shot same-session import, MIME/role filtering, independent Painting copies and corruption negatives.

**Source list to review next:** `src/greia_launcher/creation_selection.py`, `storage_broker.py`, `supervisor.py`; `src/greia_platform/creation_access.py`, `creation_client.py`, `storage_client.py`, `creations.py`, `creation_gallery.py`; `activities/painting/painting_app.py`, `activity.toml`; focused tests above.

### Honest evidence and unresolved decision

**NO tests were executed this turn**, including headless unit tests, `make verify`, Simulator, screenshot capture, socket/live Activity execution or hardware. The user's local agent is temporarily unavailable and the assistant runtime has no complete authenticated Greia checkout or Pygame. The prior source-only isolated mirror's 33/33 PASS is historical and does not verify this candidate. Do not recycle it as current PASS.

`docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P3_TRUSTED_PICKER_DISPLAY_CONTRACT.md` documents the **still-missing real modal presentation** while a consumer Activity owns the display. Greia must extend the existing display/session owner and trusted chrome contract rather than draw into a hidden Shell window or create an Activity-specific file manager. Only enable the new broker gate when that backend has a real child-visible, focus-safe, cancel-safe and session-restoring picker.

**Shape Garden correction:** actual app randomly plants transient shapes and has **no native project save**; it is not currently a persistent sticker compositor. P4 must build legitimate independent editable project support (or select a true stamp app after review) before a painting→shapes→painting round-trip is claimed.

**Entire future test carryover:** `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md` has updated pinned source SHA and covers old and new tests, true desktop screenshot checks (1024×600, 800×480, 1366×768), Painting private/share/reopen/delete, filter/role/selection security, audio preview, cancellation and later full cross-app/hardware gates. Do **not** ask the user to run it now; their agent is unavailable. The next source implementation may proceed, and when the agent returns, revise the source SHA and run that consolidated non-destructive procedure in order; stop at first failure.

**Remaining P4–P8:** runtime-backed chooser visual test, Painting consumer UI, Shape Garden saved-project and compositing, Theatre backdrop persistence, live WAV/UTF-8 producers, 75% proportional protected disk budget enforced across ALL writer services, backup/restore, curated built-in index and release review of 45 Activities, and finally real hardware only after the separate first-boot lifecycle route is accepted.


## 86. Creations P3 trusted modal + child-visible Painting import — SOURCE-WIP, execution deferred (2026-10-07)

**Authoritative workstream:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md`, sibling `PROGRESS.md`, and `P3_TRUSTED_PICKER_DISPLAY_CONTRACT.md`. This tranche remains independent from the still-open Acer install/first-boot/update lifecycle.

**Pinned latest code/test source candidate:** `dae96e9b63bb537456579fa51ad1d9539cf0c204`. Documentation commits after it only describe/route this candidate. **No tests were executed for this candidate** because the owner's local agent is temporarily unavailable and this assistant runtime does not have the complete authenticated Greia/Pygame checkout. Historical isolated mirror PASS results do not validate this newer modal code.

### Source now implemented

1. **Runtime-neutral modal lease** — `src/greia_launcher/shell_window.py` adds `ShellActivityModalLease(session_id, generation, activity_pid)` and bounded prepare/show/dismiss/abandon methods to the existing Shell-window backend contract. Native window/surface handles are backend-private; the generic lease contains no X11 IDs.
2. **Installed Legacy-X presenter** — `shell_window_legacy_x.py` extends the existing trusted Xlib seam. Immediately before showing a picker it verifies the currently focused non-Shell X11 window advertises `_NET_WM_PID == exact supervised Activity PID`, privately records that window, raises/focuses Greia's existing Shell SDL window, and restores the exact verified Activity window on dismissal. It re-proves ownership at show time so SDL window recreation after READY cannot create a stale restoration target. Missing/ambiguous PID ownership fails closed.
3. **Mandatory Home/Back remains above the picker** — `SystemChromeBackend/SystemChromeCoordinator.ensure_visible`, Legacy-X restack, and `TrustedChromeActivitySupervisor.ensure_system_chrome_visible` keep the current exact chrome lease alive and above the Shell modal. No second system-navigation implementation was created.
4. **Trusted picker host** — `src/greia_launcher/creation_picker_host.py` bridges one RUNNING Activity session to the existing filtered `CreationsGalleryScreen`, using the active profile's managed `creations_dir`. It enables the broker only after a concrete modal lease exists, drops pre-modal events, redraws only for open/input/audio progress, issues a one-use grant only through the trusted Supervisor callback, restores Activity on choose/cancel, and on abnormal cleanup cancels pending request, disables presenter authority, closes audio/UI, restores when safe and abandons the lease.
5. **Launcher lifecycle** — `LauncherApplication._launch_selected()` now services that host inside the existing supervisor loop only for manifests declaring `creations.consumes`. Modal/picker failure becomes platform failure rather than silent degradation. A `finally` teardown prevents Simulator stop or unexpected unwind from stranding a request/lease.
6. **Canonical Simulator modal** — new `src/greia_simulator/shell_window.py`; `SimulatorSystemChromeRemoteBridge` now owns exact-session Shell modal state. While active, Activity remote event drains receive no ordinary input, Shell consumes the same queued input, Activity frame uploads cannot overwrite the modal, and protected Home remains Greia-owned. `GreiaSimulatorChildShell` composes this backend; there is no Simulator-specific picker UI or selection IPC.
7. **Painting reference consumer is user-visible in source** — Painting's private gallery shows a picture-arrow-down action. It requests only `image/png`, never blocks, suppresses duplicate pending requests, polls the broker no faster than every **120 ms**, handles cancel/unavailable safely, imports only the child-selected one-use handle, validates MIME+digest and decodes before mutation, then writes a **new independent editable private painting**. Existing private autosave and explicit up-arrow immutable publication remain separate.

### Regression source added/updated — all UNEXECUTED

- `tests/test_shell_window_legacy_x.py`: exact lease, stale/foreign denial, show-time PID verification, recreated-window restore, Noop fail-closed.
- `tests/test_system_chrome.py`: restack same visible exact lease.
- `tests/test_trusted_chrome_supervisor.py`: RUNNING-session trusted restack.
- `tests/test_simulator_system_chrome.py`: modal input diversion, Home priority, Activity frame suppression, session mismatch.
- `tests/test_creation_picker_host.py`: prepare/open/draw/cancel/select callback/show failure/chrome failure/terminal Activity/abnormal teardown.
- `tests/test_painting_creations.py`: explicit PNG request scope, duplicate request suppression, bounded pending polling, cancel, unavailable picker, one-use ready import and independent-editable-copy integrity.
- Earlier creation broker/gallery/selection/security tests remain part of the same accumulated test set.

### Single deferred acceptance procedure

`docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md` now pins `dae96e9b...` and accumulates **all** earlier and current tests. When the local agent is available, run it as one non-destructive desktop source + Simulator collection. It now explicitly requires:

- focused creation/Painting/modal/chrome/Simulator suites + `make verify`;
- My Creations visual/deletion/resolution checks;
- Painting publish;
- **Painting private gallery → trusted universal picker → cancel → Painting restore**;
- repeat → select a published PNG → automatic Painting restore into a new editable private project;
- source snapshot remains unchanged after editing imported copy;
- repeated open/cancel/select without stale events/requests;
- protected Home while picker is visible ends the Activity through existing lifecycle and does not strand the modal;
- Simulator **remote web canvas** is the authoritative synthetic modal evidence. It is not proof of native macOS window stacking;
- 800×480, 1024×600, 1366×768 screenshots/input;
- no Acer flash/install/reboot in this acceptance.

### Still open

- P3: execute the full source/Simulator acceptance; actual installed Legacy-X focus/stacking evidence later; future Wayland/KMSDRM modal backend implementations.
- P4: Shape Garden has no persistent project today. Add a legitimate bounded editable picture+shape project (or choose a better existing stamp-style Activity after source/gameplay review), then flattened PNG export; add Theatre independent backdrop persistence; prove end-to-end round trip.
- P5: genuine WAV producer/preview-before-select and UTF-8 producer/consumer integration.
- P1 capacity completion: enforce proportional 75% + reserve on **all** profile-writing owners, not just CreationLibrary.
- P6–P8: explicit release catalogue, 45/45 quality review, full release/physical acceptance.

**Next source task while execution remains deferred:** deep-review Shape Garden and nearby creative Activities, choose the cleanest product direction, and implement the first persistent picture+shape project slice without changing its child fantasy into a generic desktop editor.

## 87. Creations P4 image round-trip source: Shape Garden projects + Teatrino saved backdrops — execution deferred (2026-10-07)

**Authoritative workstream:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md`, sibling `PROGRESS.md`, and the consolidated desktop/Simulator acceptance under `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md`.

**Pinned latest code/test checkpoint:** `60832f87e2ff432ccadb1189ba1cb726cb2e1394`. Documentation commits after that checkpoint only update state/instructions. **No tests were executed for this checkpoint** because the owner explicitly asked to carry this turn's tests into the next slice while the local agent is unavailable. Do not reuse earlier isolated mirror PASS results as evidence for this source.

### P4 source now implemented

1. **Shape Garden keeps its original product identity.** The existing tap-to-grow randomized shape play remains the interaction model. A new pure `GardenProject` serializes only bounded durable placed shapes plus an optional backdrop digest; transient particles, reaction timers and grow-in animation are intentionally excluded.
2. **Shape Garden private persistence.** `GardenProjectRepository` stores the selected PNG as a profile-private content-addressed backdrop, verifies SHA256 before load, commits project metadata after bytes are safe, preserves the previous committed project on metadata failure, and performs bounded orphan cleanup. Shape edits autosave and save again on ordinary exit.
3. **Shape Garden universal import/export.** Its manifest declares PNG produce+consume. The child-visible down-arrow requests only `image/png` through the existing trusted picker and polls nonblockingly; cancel/failure does not mutate the project. A selected picture becomes only the upper backdrop while soil + garden shapes remain owned by Shape Garden. The up-arrow explicitly flattens the stable project (no transient sparkles) and publishes role `composition`; unchanged in-session re-share is deduplicated.
4. **Teatrino universal backdrop import.** Its manifest now declares PNG consumption. The stage import action uses the same trusted picker; imports are disabled while recording. MIME+digest and PNG decode are validated before stage mutation. Cycling a built-in scene explicitly returns to built-in scenery.
5. **Saved-show backdrop independence.** Teatrino copies custom backdrops into its private storage as **content-addressed blobs referenced by saved shows**, so deleting/editing the My Creations source cannot break a recorded story. Multiple shows using one picture share one blob; last-reference deletion and over-cap show eviction reclaim it.
6. **Truthful Theatre persistence.** Existing silent loss was tightened. When real Greia storage exists, save/delete require a readable authoritative show index. A failed new-show file/index commit rolls back unique files and raises `ShowStorageError`. The app shows a localized failure, plays no applause and emits no `story.recorded` creation event unless save actually commits. The bounded in-memory fallback remains only for genuine no-storage/dev mode.
7. **Shared PNG hardening.** `src/greia_platform/pygame_png.py` now bounds source payload bytes, source side length/pixel count, target size and encoded output size before expensive conversion. Shape Garden/Teatrino use the shared helper. Painting still has a small equivalent local wrapper and can be migrated separately without changing behavior.
8. **Picker first-frame polish.** `ActivityCreationPickerHost` pre-renders/flips the first trusted picker frame while the Shell is still hidden, then raises it. This avoids showing an old Home framebuffer for one frame on Legacy-X; the normal launcher flip/capture after modal activation remains the Simulator authority path.

### New/expanded regression source — all UNEXECUTED

- `tests/test_shape_garden_project.py`
- `tests/test_shape_garden_creations.py`
- `tests/test_teatrino_shared_backdrop_repository.py`
- `tests/test_teatrino_shared_backdrop.py`
- `tests/test_pygame_png.py`
- expanded `tests/test_creation_picker_host.py`
- existing Painting/broker/gallery/chrome/Simulator/Teatrino suites remain mandatory.

The consolidated acceptance now adds real Simulator evidence for:
- Painting → Shape Garden import, shape persistence across reopen, flattened publication;
- Shape Garden composition → Painting independent editable import;
- Painting/Shape Garden PNG → Teatrino stage;
- saved Teatrino show retaining its custom backdrop **after the shared source PNG is deliberately deleted**;
- all earlier modal cancel/select/Home/repeated-open, resolution, gallery/delete and security checks.

No `make verify`, complete-checkout unit suite, real Pygame interaction, screenshot, microphone/audio, native installed Legacy-X, Acer/Pi or release evidence was produced. **P3 and P4 remain SOURCE-WIP.** Do not flash/rebuild/reboot hardware for this acceptance; the Acer first-boot/install/update route remains independently open.

### Next source work while the local agent is unavailable

Proceed to **P5 WAV + UTF-8 interoperability** using the same typed broker/picker architecture, and complete P1's **all-writer proportional capacity guard** rather than placing the 75% policy only around CreationLibrary. The 45-Activity release-quality review remains **0/45 accepted** and must not be conflated with source migration progress.



## 88. Creations P5 first WAV route — Voice Stories narration → Teatrino; execution deferred (2026-10-07)

**Pinned latest source/test candidate:** `cb9bc32c680ddd3953d256b8bc0c4311e194bfad`. Documentation after that SHA only updates state/test instructions. **No tests were executed for this candidate**; the owner explicitly deferred all current testing until their local agent is available.

### Source implemented

1. **Durable WAV producer:** `storie_della_mia_voce` declares `audio/wav` production and shares only private scene WAVs belonging to already-saved stories. Share role is `narration`; same saved scene is deduplicated within a session. The trusted CreationLibrary `WavCodec` remains the publication validation/canonicalization boundary.
2. **Teatrino WAV consumer:** manifest consumes `image/png` + `audio/wav`. A new compact pre-reader saved-voice control requests only `audio/wav` with role `narration`, uses the common trusted picker and polls at the same bounded nonblocking cadence as image import.
3. **Audio owner:** `ImportedNarrationTrack` in `teatrino_audio.py` validates/canonicalizes WAV via the platform codec, enforces Theatre's duration ceiling, owns mixer playback and can produce a valid trimmed PCM prefix if the child stops puppeteering early.
4. **No microphone contention:** when a shared narration is active, Teatrino REC plays that track while recording puppet motion/SFX and **does not call microphone start**. Auto-stop follows narration duration. Manual Stop trims the selected narration to elapsed time before the private show save. With no imported narration, the original microphone path remains unchanged.
5. **Snapshot independence:** the selected shared WAV exists only as an in-memory source until a show saves; `ShowRepository` then writes its own private WAV alongside JSON/backdrop state. A later deletion of the My Creations source must not break replay.
6. **Source switching:** tapping Teatrino's microphone control while a shared narration is selected clears the imported narration and returns to live microphone mode. Picker cancel/invalid role/MIME/digest leaves the prior narration untouched.
7. **Lifecycle cleanup:** imported narration and ordinary playback channels stop on completion/Activity teardown. Existing show playback now explicitly stops its audio channel at show end.
8. **Transient defect caught during static review:** commit `84f37b27...` introduced bad run-loop indentation while adding `try/finally`; it was caught immediately by source inspection and fixed at `ad9a606e...`. Do not describe the intermediate commit as runnable evidence.

### Deferred regression source

- `tests/test_voice_creations.py`
- `tests/test_voice_creations_storage.py`
- `tests/test_teatrino_audio_narration.py`
- `tests/test_teatrino_shared_narration.py`
- all earlier Creation/Painting/Shape Garden/Teatrino/modal/chrome/Simulator suites.

The single accumulated desktop procedure is still
`docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md`, now pinned to `cb9bc32c...`. It adds real disposable-profile Voice Stories recording/publication, **audible Play/Pause/Resume/Replay before selection**, narration-only Teatrino picker, imported narration performance with no mic capture, early-stop trim, saved-show replay after deleting the shared source WAV, and explicit switch back to the ordinary mic.

**No complete checkout, `make verify`, Pygame, audible/microphone, Simulator screenshot, Legacy-X or hardware test has run for this candidate.** P3/P4/P5 remain SOURCE-WIP.

### Next source direction

Implement a genuine UTF-8 text producer/consumer using Writing and only semantically compatible existing Activities. For the second audio consumer, source review currently favors **Orchestra Animali** (voice/narration backing track for child accompaniment) and rejects Officina dei Suoni because arbitrary recordings would dilute its phonemic-learning contract. P1 all-writer adaptive capacity and P6–P8 remain open.

## 89. Creations P5 reciprocal UTF-8 route — Writing ↔ Posta di Leo; execution deferred (2026-10-07)

**Latest text-source checkpoint before this documentation commit:** `8d69ee4e7ee076923fbd78256238938b76b59477`, followed by source hardening through `82c942525a80d1e9499786c55be0fc18898cec17` and test/doc commits. **No tests were executed for this tranche**; the owner asked to carry current tests into the next larger local-agent run.

### Source implemented

1. **Writing producer/consumer:** `activities/writing/activity.toml` declares `text/plain` production+consumption. Writing deliberately publishes the saved private document as role `document`; unchanged in-session content is not re-published. Its picker accepts roles `document` and `postcard` and creates a brand-new private Writing document from the one-use selection rather than overwriting the current document.
2. **Writing storage boundary:** `DocumentRepository.create_text()` writes the new body first and removes it again if the index commit fails. Import validates MIME, semantic role, SHA256 and strict UTF-8 before committing. Existing documents remain untouched on cancellation/failure.
3. **Posta consumer:** the postcard editor now has a large paper-arrow-down non-reader control. It opens the same trusted picker nonblockingly, scoped to `text/plain` roles `document` / `postcard`. Selected text is strict UTF-8 + digest checked, whitespace-compacted into a single postcard message and truncated through shared grapheme logic so emoji/ZWJ clusters are not split.
4. **Posta saved-only producer:** unsaved drafts cannot publish. A selected **saved** postcard modal exposes a paper-arrow-up action. It publishes only a durable private text source as role `postcard`; same saved card is deduplicated in-session.
5. **Posta private source durability:** `GreiaPostcardStorage` now keeps a path-safe UTF-8 file for each saved postcard, tied to the authoritative postcard index. New-card files are rolled back if the index write fails; removed-card files are reclaimed only after the index commits. Safe historical alphanumeric/hyphen IDs remain accepted for compatibility.
6. **Adjacent reliability repair:** failed postcard deletion no longer removes the card only in memory while storage still retains it. The pre-delete library snapshot is restored when persistence fails.
7. **Reciprocal independence:** Writing accepts a `postcard` item as an independent private document. Deleting either shared Creation later must not break the original saved postcard or imported Writing document.

### Deferred regression source

- `tests/test_writing_creations.py`
- `tests/test_posta_di_leo_creations.py`
- updated `tests/test_activity_posta_di_leo.py` private-file storage seam
- all prior P1–P5 Creation/PNG/WAV/modal/Simulator suites remain accumulated.

The one authoritative deferred procedure remains `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md`. It now includes Writing→Posta import with emoji/newlines/overlong text, saved Posta→Writing reciprocal share, cancellation/failure preservation, and deletion of shared sources while private copies remain usable.

**Evidence boundary:** no complete checkout, `make verify`, Pygame typing/rendering, trusted text picker screenshot, Simulator, Legacy-X, Acer/Pi, storage-failure execution or physical acceptance has run for this UTF-8 tranche. P3/P4/P5 remain SOURCE-WIP.

### Next source direction

Deep-review `Orchestra Animali` before implementing the second audio consumer. Only proceed if child-supplied WAV meaningfully fits its current musical interaction without diluting pedagogy. Then complete P1 proportional capacity enforcement across every profile-writing owner. P6–P8 and the 45/45 release review remain open.

## 90. Creations P5 second WAV consumer — Orchestra Animali durable play-along backing; execution deferred (2026-10-07)

**Pinned latest Orchestra source/test checkpoint before docs:** `ae4e5bf6bea6a1adf070de4092c62383056ff17d`. **No tests were executed for this tranche**; all checks remain accumulated for the next local-agent desktop acceptance.

### Source implemented

1. **Product fit:** current Orchestra source is free musical exploration (five synthesized instrument cards + rainbow piano), not an implemented auditory-memory sequence game. Shared child WAV is therefore used only as an optional play-along backing track.
2. **Private ownership:** new `orchestra_backing.py` persists one content-addressed private WAV plus authoritative metadata. Mutations refuse unreadable metadata, roll back a unique new blob if the pointer commit fails, and remove the replaced blob only after successful commit.
3. **Typed audio owner:** `ImportedBackingTrack` reuses `WavCodec` canonical validation; `BackingTrackPlayer` reserves mixer channel 0 and owns explicit Play/Pause/Resume/stop/natural-completion state. Existing synthesized instrument and piano sounds remain the ordinary live overlay.
4. **Trusted picker:** Orchestra requests only `audio/wav` roles `narration`, `song`, or `music`, polls at the common bounded 120 ms cadence, validates MIME/role/SHA/WAV before state mutation, and persists the selected canonical WAV before loading it into the player.
5. **Audio isolation:** if a backing track is playing, opening the universal picker stops it first so My Creations preview audio has sole ownership. Cancel keeps the selected private track ready but does not resume/autoplay.
6. **Persistence semantics:** relaunch restores the private track in `ready` state, never autoplay. Deleting the shared My Creations source later must not break Orchestra playback.
7. **Pre-reader UI:** top-safe music-note/down-arrow import and large Play/Pause controls were added without moving the instrument stage. Import is visibly disabled and has no hit target if trusted Creations/private storage is unavailable.
8. **Concert meaning:** live instrument/piano taps are counted only while backing audio is playing. `concert.performed` is emitted at natural backing completion only if at least one live input occurred; passive playback is not a creation.
9. **Adjacent manifest defect repaired:** source had emitted undeclared `instrument.played` while declaring unused `melody.matched`; Greia's history authority rejects undeclared events. Manifest now matches actual behavior (`music`, `rhythm`, `creativity`; events `instrument.played` and `concert.performed`) and declares `audio/wav` consumption. Repository search found no progression or other source references to the removed legacy event IDs.

### Deferred regressions

- `tests/test_orchestra_backing_store.py`
- `tests/test_orchestra_creations.py`
- `tests/test_orchestra_manifest.py`
- all earlier P1–P5 Creation/PNG/WAV/UTF-8/modal/Simulator suites.

The single acceptance owner remains `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md`. It now includes audible preview-before-select, no-autoplay import/relaunch, rapid live accompaniment without channel theft, Play/Pause/Resume, picker-preview isolation, source-WAV deletion independence and concert semantics.

**Evidence boundary:** no complete checkout, `make verify`, Pygame/SDL mixer, audible Orchestra playback, Simulator screenshots, Legacy-X, Acer/Pi or physical evidence was produced. P3/P4/P5 remain SOURCE-WIP.

### Next source direction

Return to P1 and enforce the proportional machine-capacity policy across **all authoritative profile writers**, not only CreationLibrary: real writable-volume ceiling (~75% used maximum), protected free headroom, existing per-Activity namespace/file bounds, fail-closed mutation semantics, and no Acer-specific tiny fixed global quota on larger disks. Keep this centralized at platform storage authorities rather than duplicated inside Activities.
