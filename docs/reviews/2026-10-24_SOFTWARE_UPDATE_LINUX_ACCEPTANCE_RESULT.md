# Software update Linux acceptance result

Date: 2026-10-24
Status: **PARTIAL PASS; Session 04 remains OPEN; clean fixed-source rebuild NOT RUN**
Work order: `docs/testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md`
Host: Ubuntu 24.04 x86_64, KVM, QEMU 8.2.2, Python 3.12.3, 8 vCPU
Evidence root: `/var/tmp/greia-software-update-e8fed0ec494763834114e49863cc64aa66e70f2e-20261024T155314Z/`
Secondary evidence: `/var/tmp/greia-software-update-e8556dd99bfcccffbcb85cc34378fefdd5c87a76-20261024T143830Z/`

This run found and fixed real source/build defects. The successful installed
apply tests below were executed on a disposable clone of the RC image built at
`e8fed0ec4`, with the initial Parent Activity generation manually repaired to
`0755`. The committed source fix (`0bf1e15e6`) was **not rebuilt into a clean
installer and re-installed** before the run stopped. Do not read the repaired
clone as a clean fixed-source image acceptance.

## Source and gates

- Run start: `e8556dd99bfcccffbcb85cc34378fefdd5c87a76`.
- Verifier fix committed: `e8fed0ec494763834114e49863cc64aa66e70f2e`.
- Parent Activity generation fix committed: `0bf1e15e6a60fa4c5cdbc7f8b62d7c0880dc1bee`.
- Focused package/update gate at `e8fed0ec4`: **125/125 PASS**
  (`software-update-focused.log`, exit 0). Includes
  `test_rc_image_contract`.
- Full `make verify` at `e8fed0ec4`: **5,943 tests, 8 failures, 3 errors, 2
  skips; NOT GREEN** (`make-verify.log`). Failures were the documented Foresta
  content (3), Parent Wi-Fi source assertions (2), MBR message wording (1),
  `morbidi_mostriciattoli` timing budget (1), and an additional aggregate-only
  `piccola_serra` timing budget (1). Errors were the known ARM64 profile error
  and two missing optional voice modules on Linux (`huggingface_hub`,
  `mlx_audio`). A clean pre-update worktree at `4eaad2547` reproduced the same
  voice-module errors, ARM64 error and `morbidi` timing failure. The full gate is
  not relabeled green.

## Source fixes made during acceptance

1. **RC installer verifier extraction** (`e8fed0ec4`,
   `tools/verify-development-installer.sh`): the target contract extracted only
   `opt/greia-os/assets`, losing the generation symlink and the Activity-index
   alias, so every correct RC image failed with "installed /opt/greia-os is not
   the application-generation symlink". The verifier now extracts the target
   symlinks and base generation index; a regression test was added. The
   already-built image passed the corrected verifier.
2. **Initial Parent Activity generation permissions** (`0bf1e15e6`,
   `src/greia_platform/activity_packages.py`): the initial `gen-000001` was
   published through `mkdtemp` with mode `0700`, owned by whichever process
   initialized it. A root-side update produced `root:root 0700`; `greiakid`
   could not traverse it and the child launcher exited in a loop after the
   pointer switch. Creation now publishes `0555`, and existing non-traversable
   generations are repaired. A regression test was added; focused
   `test_activity_packages`, `test_software_update_generation` and
   `test_software_update_bootstrap` passed 37/37.

## Passed installed predicates (repaired disposable clone; not clean rebuild)

- Single-root RC GUI install: PASS. Real installer flow (language, keyboard,
  target, pointer, display, Wi-Fi, 2-second erase hold) completed; target
  `/dev/sdb`, 16 GiB. Screenshots retained under `gui-screens/`.
- Installed guest facts: PASS. Bootstrap marker exact, helper executable, apply
  timer `enabled`, recovery service `active`, `/opt/greia-os ->
  greia-software/generations/base`, Activity-index alias correct,
  `/dev/sda1` 16.8 GB with 15.2 GB free.
- Real child profile: PASS. First-child GUI wizard created `TEST`; the profile
  picker and child home rendered; profile survived all later updates and
  rollback.
- Parent pairing over HTTPS: PASS. Trusted certificate saved; default
  `greia` password bootstrap issued a device credential; `GET
  /api/v1/system/update` reported `upload_available=true`.
- Durable upload receipt: PASS. `POST /api/v1/system/update/package` returned
  HTTP `202` only with `package_bytes == received_bytes`; job IDs:
  `47670b97afa644c29ec7d317932278ef` (first attempt),
  `fb36643edab94d9d9c0bce20b04f49ba` (apply 1),
  `4bd6b816eae44eec85ff3dc20b9c4d0d` (apply 2).
- Python apply after the generation-permission repair: PASS. `queued ->
  validating -> waiting_for_idle -> restarting -> applied`; pointer switched to
  the candidate generation, Parent `/healthz` returned `{"status":"ok"}`, and
  `launcher_interactive_ready` was emitted after the switch.
- Second Python apply with a newer identity: PASS
  (`0.13.2-acceptance`); pointer advanced and the previous generation remained.
- Child-active idle fence: PASS. With `Fluffy Monsters` active, the second
  Python job stayed `waiting_for_idle` and the pointer stayed on
  `app-fb36643edab94d9d9c0bce20b04f49ba`. Returning through the real profile
  picker (protected profile control; `xdotool` click on the guest X session)
  let the same job reach `applied`.
- Built-in Activity `one`: PASS (`writing`, job
  `9dd6c01ccc2248658fcc8ec704d2a6d2`). Index kept 45 IDs, built-in trust.
- Built-in Activity `set`: PASS (`writing` + `painting`, job
  `42dc71b5485e4beab9a756327642021e`). Index kept all 45 IDs; both listed
  activities present; trust `built_in`, source `greia-system`.
- Built-in Activity `all` (source roster): PASS (job
  `41aa51b2a8c5406ca97aecb77e796d9a`). Index kept 45 unique IDs.
- Installed-root `all` built with `--all-from-installed-root` from the real
  mounted installed root (45 IDs): PASS (job
  `50e92a1d244544d1b29e9fb243fe7938`).
- Combined Python + `writing` from the fixed source: PASS (job
  `e11f9bdecd6944bfa7852ef79ba0821f`). Active generation contains
  `os.chmod(staging, 0o555)` and the 45-ID built-in index under the same
  generation ID.
- Startup-failure rollback: PASS (job
  `b65c8013a82e4f90bf32a5b75216d42b`). The valid package raises at
  `greia_launcher` import; the job reached `rolled_back` with
  `error_code=launcher_not_ready`, the previous generation
  (`app-e11f9bdecd6944bfa7852ef79ba0821f`) was restored, launcher and Parent
  returned, `/healthz` was `{"status":"ok"}`, and the profile picker still
  showed `TEST`.
- Subsequent valid update after rollback: PASS (job
  `0edc410b99b743ffbe8be5ab6469d5ff`), `applied`.
- Interrupted trial recovery: PASS. The first failed attempt
  (`47670b97…`) was power-cut while the journal was `trial`; cold boot restored
  `base`, cleared the pending/candidate job, and reported `rolled_back` with
  `interrupted_activation`.

Package digests retained in
`packages/SHA256SUMS`; examples: Python 1
`c295cbfcd63234af0de93e4c31be32f468b8c4e7f2e25fc8f9424bc884ff1c35`,
Python 2 `6f99d168725cc9354108273101e529091e4fda33f2e0b37ed7d0a50f79d8175b`,
combined `816e63b68064b684fca4470bebb6a31be75fdafdffa877b6fbfed7754fc091a1`,
startup failure `b960806dbbad5fbc276d4c21272c97be4577e9d3466391bb8caf78c6b29dc705`.

## Failures / blockers

### BLOCKED — Acer A/B owner release and product harness

`tools/greia_release.py build --version 0.13.0-phase0-dev` refused:

```text
Release build refused: ERROR: boot cover 'greia-early-framebuffer-v1' is not
registered as release-safe; a noninteractive branded-only backend must pass its
acceptance gate first
```

The tool always sets `PIP_RELEASE_BUILD=1`; no boot-cover backend is registered
release-safe. No A/B installer or v3 bundle was built, so the A/B product
harness, full-system wrapper, A/B package cases and A/B restart/rollback legs
were **NOT RUN**. Older A/B artifacts on the host (Sept 26 installer, Sept 18
source bundle) predate the software-update engine and were not used.

### BLOCKED — Parent-source Activity seeding/updates

`POST /api/v1/activities/install` is advertised
(`activities.install=true`) and is developer-enabled on the RC image, but
returned HTTP 400:

```json
{"error":{"code":"activity_install_rejected","message":"could not establish
Activity package transaction lock: [Errno 1] Operation not permitted:
'/var/lib/greia-os/activity-packages/generations'"}}
```

The root update service initialized the Parent Activity state tree as
`root:root` (`generations`, `versions`, `receipts`, `staging`); the Parent
service runs as `greiapanel` and cannot chmod/write it. The launcher could read
the repaired `gen-000001` after the source fix, but the Parent route cannot
install. Parent-source `one`/`set`/`all` and `combined` Parent-trust rejection
were **NOT RUN**. A clean fixed build should avoid creating the Parent state
tree from the root updater, and the shared tree needs a deliberate
`greiapanel`/`pipprofiles` ownership model.

## NOT RUN / open

- Clean RC rebuild and fresh install from committed `0bf1e15e6`; all successful
  installed tests above used the repaired `e8fed0ec4` clone.
- Partial-stream upload / no-`202` / no-candidate-negative check.
- Receive-reserve HTTP `507` low-space check and retry.
- Parent-stop-after-durable-`202` helper leg.
- Observed `applying` power-cut (the observed cut was in `trial`/`restarting`).
- Full-system `.greia_update` wrapper, A/B first boot/update/rollback, PERSIST
  acceptance.
- Production-art child creations/saves: the `TEST` profile survived, but no
  creations were seeded and hash-compared before/after.
- Mobile-client upload; only the host streaming/HTML-equivalent Parent API
  route was used.
- Physical hardware and USB media acceptance. The authorized 8 GB LaCie
  (`/dev/sdc`, iamaKey) was **not modified**; the work order forbids flashing
  host media for this acceptance.

## Next exact actions

1. Fix the Parent Activity state-tree ownership boundary so the root updater and
   `greiapanel` do not create competing root-owned shared state; add focused
   tests.
2. Rebuild the RC installer from the closed source SHA and re-install a fresh
   disposable target; rerun the Python apply, idle-fence and rollback cases
   without manual repair.
3. Resolve the release-safe boot-cover gate (owner acceptance or an explicit
   owner-approved A/B development fixture) before claiming A/B/full-system
   acceptance.
4. Run the remaining §7/§11 fault recipes on disposable clones.
5. Keep Session 04 OPEN; no release or physical-hardware claim is made.

## Source follow-up after this Linux run (2026-10-24)

Source freeze: `ab02b9ec6fc7108e7b873b2b2c8c68eefd47ff18`. The post-commit rerun executed
170 tests in 17.955 seconds, **OK with 1 Linux-only skip**; exact log:
`/tmp/greia-acceptance-followup/focused-ab02b9ec6.log`. The later evidence
commit changes documentation only; the full gate remains NOT GREEN as below.

The subsequent source tranche addresses the shared-store ownership blocker,
including root-written lock/receipt/generation ownership and legacy store
repair. It also fixes a concurrent initializer chmod race found by the local
full suite, preserves read-only hardlinked generation files during cleanup,
and covers the legacy directory migration and Parent umask paths.

A separate, explicitly experimental `build-acceptance-fixture` command now
reuses the validated Acer A/B pipeline while retaining the production release
boot-cover gate. Its report is non-release-eligible and the index builder
rejects it. Use the revised work orders for the next/reverse fixture commands;
this is a VM acceptance route, not production release or boot-cover approval.

Independent source reviews and 170 focused tests (one Linux-only identity skip)
passed on macOS. The full follow-up gate is NOT GREEN: its first run exposed
the now-fixed initializer race plus prior failures, and the final retry aborted
in native Pygame audio code without a summary. Exact logs and disposition are
in the current HANDOVER entry. These source checks do not change any PASS,
FAIL or NOT RUN from the Linux execution above. A clean committed-source RC
rebuild/reinstall and A/B fixture run remain required, without manual guest
permission repair. Session 04 remains OPEN.
