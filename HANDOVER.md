# Greia — Current Engineering Handover

**Updated:** 2026-09-21
**Canonical repository/branch:** `frozenpepper/Greia` / `main`
**Frozen baseline:** `372ee310f8e9a652bb88ecce75168e62928489e7` (clean tree)
**Version:** `0.13.0-phase0-dev`
**Primary blocking platform phase:** **post-R1 product-composition closure — T3-P OPEN/BLOCKING; install/update/release/multiplatform lifecycle now routes to `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md` (ADR 0036 successor). Gate-P5/V12G/D6 closure routing below is historical and superseded for lifecycle sequencing**
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
