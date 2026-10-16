# Gate-P5 Closure V12G — Decision Report (2026-09-15)

**Run:** T-BAG R1 — `COMPLETED` (run completion, **not** product GREEN).
**Product verdict:** Gate P5 **OPEN** (0/9 predicates GREEN), T3-P **OPEN/BLOCKING**.
**Blocking defect:** new shipped defect **D6** — the A/B slot streamed from any
V12E/V12F/V12G-minted bundle cannot execute `apt-get` inside `chroot`.
**Decision required:** D6 repair side (A vs B, §7) before any further closure re-run.
**Do NOT mark T3-P DONE.**

This document is the owner decision pack: what was done, what is RED and why
(with the full D1→D6 chain), which decisions are already taken, which decisions
are yours, the two D6 repair options with consequences, and the concrete next
moves. Facts are separated from inference throughout. Evidence paths are
absolute within the repo or named orbiter locations pending cleanup.

---

## 1. Executive summary

| Item | State |
|---|---|
| T-BAG run R1 | `COMPLETED` 2026-09-15T16:01 UTC — bootstrap 141 + postr1 130 tasks all terminal (`integrated`/`accepted`/`superseded`), takeover empty, backlog 0, no live work |
| Gate P5 (`LEGACY_PRODUCT_PATH_GREEN`, schema `gate-p5-closure-v1`) | **OPEN** — 0/9 predicates GREEN on V12G |
| T3-P exact shipped product composition | **OPEN / BLOCKING** (source composition T3-S DONE; shipped product composition not) |
| V12G (`POSTR1-P5-GATE-CLOSURE-V12G`) | **Integrated as attempt-correct FAIL RED** — implementer `FAIL` → fresh reviewer `PASS` endorsing the RED verdict (PASS endorses the *attempt*, not the gate) |
| D5 (`CAP_SYS_CHROOT`) | **Proven effective on the live product path** (V12F EPERM → V12G exec-ENOENT stage advance) |
| D6 (new) | **Isolated with production-path proof + slot-byte forensics**; deterministic; correctly left red (outside lane Allowed changes) |
| D4 (`cryptography`/`system-update`) | Intact at all stages in V12G (live + target manifests) |
| Footprint | 985 MiB < required 1000 **PASS** (preferred-≤800 warning retained) |
| Local suites (fakes-only) | 92/92 GREEN (`test_installer_unit_contract` 19, `test_gate_p5_closure` 17, `test_build_profiles` 9, `test_profile_manifest_contract` 6, `test_install_transaction_service` 38, `test_installer_hardware_support_service` 3) |
| Full `make verify` (~500 s) | Not re-run on V12G (no source changed; focused surface covers the delta — reviewer-judged, see §9 uncertainty) |

**The single sentence that matters:** the installer got *one stage further* than ever
before (past `chroot(2)` permission), then hit a *different, deeper* shipped defect:
the slot it is told to `apt-get` inside contains no `apt-get` to run.

---

## 2. What this run was, and what "COMPLETED" means

- **R1 scope:** bootstrap goal/planning tranches (141 tasks) + post-R1 product-composition
  closure `postr1` (130 tasks). All 271 tasks are terminal. No `Follow-up obligations`
  headers were filed by the final reviewer, so no mechanical triage gate is pending.
- **COMPLETED ≠ GREEN.** The run exhausted its *registered* obligations. Its final
  integrated result is an **honest RED**: 0/9 GREEN with reasons, lane status, and a
  new defect isolated — exactly the red branch the V12G brief preregistered as
  acceptable (9/9 GREEN *or* the exact red/`BLOCKED` result with evidence).
- **Nothing was laundered.** No predicate weakened, waived, or proxied; no fixture hack
  to force green; positive control executed RED-as-expected; docs-only delta
  (`HANDOVER.md` §25 + header, two plan ledgers; commit `54d87e13`; tree clean).
- **Why finish instead of replanning inside R1:** the D6 repair is a *product/architecture*
  fork (full-Debian payloads vs dropping the in-slot-`apt-get` assumption) whose
  Allowed-changes surface (`src/greia_installer`, `src/greia_platform`,
  `tools/greia_update.py`, `build/*`) sits outside every frozen closure-lane brief.
  The parent cannot invent that graph; it needs your side decision first (§7), then a
  new repair task + rebuild + V12H closure task.

---

## 3. Work done in this final stretch (V12E → V12G)

### 3.1 V12E (2026-09-15) — RED, new defect D4
- Re-ran full closure on the owner-restored orbiter lane at HEAD `0afa1b96`.
- Official `acer-aspire-one-i386-ab` image rebuilt (1318060032 B, sha `036f6ea9…`,
  footprint 981 PASS). D3 verified fixed in the artifact.
- Real install-execute leg timed out (guest to login, never powers off) — 0/9 GREEN.
- Journal-to-console replay isolated **D4**: the install-transaction service dies
  verifying *any* release signature (`requires python3-cryptography` ← module absent
  from the built live root). Composition cause: the A/B profile omitted package-set
  `system-update` while shipped services fail-closed require it.

### 3.2 D4 repair — `POSTR1-P5-SYSTEM-UPDATE-INCLUSION` (integrated after fresh Review)
- Product/build-authority decision taken: accept the `system-update` set for the A/B
  profile (both scopes — `build/profiles/acer-aspire-one-i386-ab.toml:46,48`).
- Verdict: `cryptography` present in V12F/V12G builds at both levels
  (`python3-cryptography 38.0.4-3+deb12u1` in live AND target manifests); zero
  crypto/signature errors before `finalize` in V12F/V12G serials. D4 closed.

### 3.3 V12F (2026-09-15) — RED, new defect D5
- Re-ran the identical closure chain against the D4-fixed HEAD. 0/9 GREEN.
- Isolated **D5**: the shipped `greia-install-transaction.service` runs
  `chroot <slot> apt-get …` (3 legs, `hardware_support_install.py:61-78`) but its
  unit lacks `CAP_SYS_CHROOT`, so `chroot(2)` dies EPERM:
  `chroot: cannot change root directory … Operation not permitted`.
- Product-authority fork recorded: grant the capability vs remove `chroot` from the
  install path. The contract test pins the current set and must move with the decision.

### 3.4 D5 repair — `POSTR1-P5-INSTALLER-CHROOT-PRIVILEGE-FIX` (integrated after fresh Review)
- Product-authority decision taken: **grant** (`CapabilityBoundingSet` /
  `AmbientCapabilities = CAP_SYS_ADMIN CAP_SYS_CHROOT` in
  `build/installer-overlay/etc/systemd/system/greia-install-transaction.service:72-73`).
- Proof (not substitution): on a disposable 1 GiB ext4 loop target off the built live
  root, old caps reproduce V12F EPERM byte-identical (exit 10/125); repaired caps
  complete the leg (`INSTALL_OK: ['firmware-ast']`, update/install/clean RC 0,
  `dpkg -l → ii`). Evidence:
  `POSTR1-P5-INSTALLER-CHROOT-PRIVILEGE-FIX/attempts/implementer-1/`
  (`d5-status.json` + `proof-excerpts.txt`).

### 3.5 Test-scope hardening — `POSTR1-P5-INSTALLER-SVC-TEST-SCOPE` (integrated after fresh Review)
- Test-only change to `tests/test_installer_hardware_support_service.py`: new
  `_directive_text` helper evaluates **systemd directive lines** (drops blanks and
  `#`/`;` comments) instead of whole-file substring scan.
- Why: the old guard false-RED tripped on a shipped-unit *comment reword* during the
  D5 task. Both negative guards (`apt-get`/`curl`/`wget` absence; pool-var absence on
  the UI unit) now scan directives; new `test_directive_scope_positive_control`
  proves both directions; sensitivity re-proven in-memory against the shipped units
  (both carry 0 guarded tokens in directives today). Full local suite 3388 OK at that
  point (baseline 3387 + 1 new, no new failure). Touches the test file only.

### 3.6 V12G (2026-09-15) — RED, D5 proven effective, new defect D6
- Cold attempt `implementer-5` (after a runtime saga — §5) re-ran the full closure at
  HEAD `98b06079` (D5 + D4 + D3 + test-scope integrated; tree `7657e5cb`).
- Lane: key mode 600, key-only `ssh orb`, `sudo -n → root`. Prior residue from the
  tree-identical checkpoint `6cf3fef1` treated as ABSENT (not SHA-bound to this HEAD);
  fresh `git archive HEAD` (tgz sha `bd8dc86d…`, match both sides) → orbiter
  `/tmp/greia-p5-v12g5-src`, D5 caps + D4 selection confirmed in the delivered tree.
- Keys/bundles re-minted through production builders only (fresh ed25519
  `greia-release-main`; 64 MiB ext4 base payload; seq20 `c66d46bc…` / seq21
  `5e2d611d…` / seq23 `1526ce11…`, all `sig_verified=True`).
- Official image rebuilt with `GREIA_AB_*` on the sudo line: **1320157184 B**,
  sha `3d3a01de…`, footprint **985 < 1000 PASS**. Built-artifact proof (read-only
  loop + unsquashfs, single unmounts): `profile.id=acer-aspire-one-i386-ab`
  (installer + target); crypto present both levels; built live unit declares exactly
  `CAP_SYS_ADMIN CAP_SYS_CHROOT`; target enables `greia-system-update.socket`.
- Closure (`/tmp/greia-p5-v12g5-closure.py` sha `c4d9cd07…`, frozen P5.4 baseline,
  pinned HEAD, run as root): positive control RED-as-expected (`d31_fn=None` →
  BLOCKED naming the unpinned D31 mapping, `closure.log:3-4`); real
  `qemu-system-i386 greia-product-install-execute` leg genuinely timed out after
  **1200 s** (guest at login prompt, never powers off; `closure.log:5-28`).
- Result: **0/9 GREEN** — died in install-execute, no predicate evaluated, none
  proxied. P5.4 record `NOT_READY`; D31 seed, RC-4 map, `source_image_mutated`
  refusal-carry all unexecuted by red necessity.
- Diag replay (disposable copy of the run clone; only console flags added to one
  grub.cfg linux line; run clone untouched; serial 9901 B) shows the **V12F-identical
  call chain** diverging only at the final errno (§4.3).
- Outcome recorded append-only (`HANDOVER.md` §25 + header, remediation-plan ledger,
  lifecycle-takeover note; commit `54d87e13`). T3-P left OPEN. Lane left healthy
  (own loops detached, no stray mounts; diag QEMU operator-SIGTERM'd only after the
  decisive traceback — its "QEMU EXITED" line is driver-logging imprecision, guest
  never powered off).

---

## 4. The RED, in full detail

### 4.1 Gate P5 — what "0/9" means
Gate `LEGACY_PRODUCT_PATH_GREEN` (`tools/x8_qemu/gate_p5.py:49`,
`run_gate_p5_closure_product:703`) requires **one full orbiter product-unit lifecycle**
with all nine preregistered predicates GREEN:

1. `full_lifecycle_green` — install → boot A/health → update B/health → unhealthy
   candidate/recovery → accepted B → D31 → reverse A, end-to-end on the orbiter lane;
2. `broken_candidate_recovers`;
3. `d31_survives` (seeded `d31_fn` + P5.4 live record);
4. `budget_768_green`;
5. `no_harness_substitution` (every claimed leg a real installed-service path);
6. `sha_bound` (image/bundles/driver/archive bound to the tested HEAD);
7. `boot_perf_green`;
8. `provenance_refusal_green` (`source_image_mutated` refusal carried);
9. `rc4_checkable` (8-step RC-4 traversal map executed).

V12G status: the run **died in step 1's install-execute leg** (in-guest
`TransactionServiceError` → guest idles → host 1200 s timeout). Predicates 2–9 were
**unexecuted, not evaluated** — 0/9 GREEN with zero proxying. The positive control
(`d31_fn=None` → BLOCKED) proves the driver *can* report BLOCKED honestly.

### 4.2 The D1→D6 shipped-defect chain (each new defect is line-of-sight, not a regression)

| ID | Stage reached | Symptom (in-guest / product path) | Root cause (shipped) | Fix decided | Proof it worked |
|---|---|---|---|---|---|
| D1 | install activation | `greia-install-transaction.service` spawns without `LISTEN_FDS`; install impossible | socket activation missing fd passing on all three services | native `LISTEN_FDS` + fd 3 (`POSTR1-P5-SOCKET-ACTIVATION-FIX`) | V12C: D1 gate PASSES, both socket wants-links present in the built image |
| D2 | update/recovery legs | `greia-system-update.socket` never enabled/started anywhere | payload lacks the wants-link; no puller | enable in `build/build-image.sh` (same task) | V12C image carries the link; legs reachable |
| D3 | install-prepare | `ServiceState.from_target_profile` raises `target image profile misses release facts` | live `target-image-profile.json` carries `profile.profile_id`, service+client contract `profile.id` (writer serializes the dataclass field name; contract suites masked it with hand-written `id` fixtures) | writer-vs-reader ownership decided product-side; payload + live both canonical `profile.id` | V12E: D3 verified fixed IN the built artifact |
| D4 | install `finalize` (signature verify) | `release signature is not trusted: Ed25519 … requires python3-cryptography` ← module absent from built live root | A/B profile omits package-set `system-update` (header deferred it pending footprint delta) while services fail-closed require it | accept `system-update` for the A/B profile, both scopes (`acer-aspire-one-i386-ab.toml:46,48`) | V12F/V12G: crypto `38.0.4-3+deb12u1` in live AND target manifests; zero crypto errors before `finalize` |
| D5 | install `finalize` → hardware-support leg (`chroot`) | `chroot: cannot change root directory … Operation not permitted` (EPERM at `chroot(2)`) | unit runs `chroot <slot> apt-get …` ×3 without `CAP_SYS_CHROOT` | grant `CAP_SYS_ADMIN CAP_SYS_CHROOT` (unit lines 72–73) | V12G product path: EPERM gone, failure moves one stage to exec-ENOENT (§4.3); loop-target proof `INSTALL_OK` |
| **D6** | install `finalize` → hardware-support leg (`exec`) | `chroot: failed to run command 'apt-get': No such file or directory` (ENOENT inside the new root) → `FreshAbInstallError` → `TransactionServiceError: fresh A/B install refused` | `fresh_ab_install` streams `open_bundle_payload_stream(bundle)` **verbatim** into slot A, then `finalize` runs `chroot <slot> apt-get update/install/clean` — but the minted 64 MiB bundle payload contains only `{etc,lost+found,run,var}` (no `/usr`, no `apt-get`) | **UNDECIDED — yours (§7)** | Forensics + source ordering close the chain deterministically (this report, §4.3) |

Earlier V12B/V12D lane incidents (poisoned resume session; worker-caused host
unmount via raw `umount -R` on shared-propagation bind mounts) are *lane* events,
not product defects, and are closed with hygiene rules (§8.3).

### 4.3 D6 — the decisive evidence (fact vs inference)

**Observed fact 1 — the errno advance (directly observed in-guest serial).**
Identical call chain in V12F and V12G
(`slot_writer.finalize:1159 → slots:173 → block_slots:679 → slots:126 →
hardware_support_install:61 → device_seams:143`), diverging only at the final errno:

- V12F: `chroot: cannot change root directory … Operation not permitted` (EPERM —
  the kernel refused `chroot(2)` itself);
- V12G: `chroot: failed to run command 'apt-get': No such file or directory`
  (exec-ENOENT — `chroot(2)` was *permitted*; the kernel then could not `exec`
  `apt-get` inside the new root).

`diag-execute-serial.log:75-127` carries the full traceback with zero crypto/signature
errors before `finalize` (D4 gate passed). EPERM-gone ⇒ D5 effective. This half is
closed without needing the slot listing.

**Observed fact 2 — the source ordering (read in-repo).**
`src/greia_installer/fresh_ab_install.py:442-501` (`open_bundle_payload_stream`) +
`:680-729` (stream verbatim via `SlotWriter.write`, then `SlotFinalizer.finalize`
with the chroot-based `package_installer`); `hardware_support_install.py:61-78`
(3× `chroot <slot> apt-get …` via argv arrays). The order is
*stream-payload → chroot-apt-get*. If the payload has no `apt-get`, ENOENT is
deterministic for **any** bundle minted by the V12E/V12F/V12G procedure.

**Recorded orbiter evidence (corroborating, not load-bearing for the verdict).**
Read-only loop-mount forensics of slot A on the quiescent disposable target: slot
holds ONLY `{etc,lost+found,run,var}` — the raw 64 MiB bundle payload — no `/usr`,
no `/bin`, no `apt-get`. Lives in orbiter `/tmp` forensics + `v12g5-status.json`;
the reviewer did not re-mount it from the read-only project view, but in-guest
ENOENT + source ordering already make the defect deterministic, so the verdict does
not rest on re-mounting.

**Falsified alternatives.** Missing-mount (error is exec-ENOENT, not mount
EPERM/ENOENT; `run/` mountpoint exists and handling unchanged); PATH-search artifact
(slot has no `/usr` at all); diag-artifact (mutations confined to the disposable
copy's grub console flags; run clone untouched); QEMU-artifact (capability/exec law
identical on Acer hardware).

**Why D6 is new, not a regression.** V12F died one stage earlier (EPERM), so no
earlier run could reach exec-ENOENT. Implicated composition files untouched by the
V12G delta. Consistent with §§16–25 history.

**Scope boundary (why it was left red).** Resolution touches `src/greia_installer` +
`src/greia_platform` + contract tests (possibly `tools/greia_update.py`, `build/*`) —
all outside the closure lane's Allowed changes. Attempting it there would have been
scope drift; the worker correctly refused, exactly as with D3/D4/D5 before their
own product decisions.

---

## 5. Runtime saga inside V12G (why it took 5 implementer attempts + recovery)

This matters because it consumed the entire 2 h budget once and poisoned a session;
it is **not** product evidence, but you should know it to trust the verdict.

1. `implementer-1` did ~30 min of valid on-plan work (lane check, clean archive,
   production minting seq20/21/23, detached official build, focused suites green,
   closure driver staged), then its session log went silent at 12:42 UTC during a
   long `sleep 540` build poll. The launcher verified silence at the deadline and
   SIGTERM'd it (exit −15, in-progress report, `changed_count: 0`). No gate result.
2. `implementer-2/3/4` were same-session resumes of `ses_f5b046cd0ffe…`; each died in
   ~15–20 s with a single non-retryable provider error
   (`APIError 400 … reasoning encrypted_content was not issued to this caller`,
   exit 1, launcher-placeholder, zero project movement). Transport failure, not
   worker failure.
3. After 3 consecutive instant deaths the harness mechanically routed the session to
   `recovery-required`, abandoned it, and commissioned Analyst `recovery-1`, which
   proved: nothing mutated anywhere (all scope-diffs empty, worktree byte-clean);
   same-session continuation impossible, must not be retried (`resume_session=null`);
   the brief is feasible in one attempt (V12F did build+closure in 1 h 41 m).
   Disposition `RESUME` recorded via the legacy `--outcome resume` fallback (report
   carried **`RESUME`** in prose but no first-line routing token).
4. Cold `implementer-5` (fresh session `ses_f5a8ede9…`) ran 0→RED in ~100 min and
   delivered the verdict above. Reviewer-1 PASSed the attempt (92/92 local re-run +
   full log/source tracing), task accepted → integrated (docs-only `54d87e13`).

Lesson carried: detached official builds + long blocking `sleep` polls on the
`muse-spark` runtime risk a provider hang; the recovery report recommends using the
build window for local suites/artifact proof rather than long blocking polls, and
never reusing a session that hard-failed replay.

---

## 6. Decisions already taken (binding — do not relitigate without new evidence)

| # | Decision | Decided by / where | Effect |
|---|---|---|---|
| 1 | D1+D2 socket-activation fix (native `LISTEN_FDS` + fd 3; enable update socket in `build/build-image.sh`) | product authority, `POSTR1-P5-SOCKET-ACTIVATION-FIX`, reviewer PASS | install/update legs reachable; verified in V12C image |
| 2 | D3 writer-vs-reader ownership (`profile.id` canonical both sides) | product authority | V12E artifact carries canonical `profile.id`; D1 gate passes |
| 3 | D4: accept `system-update` set for the A/B profile (both scopes) | product/build authority, `POSTR1-P5-SYSTEM-UPDATE-INCLUSION` | crypto present both levels; footprint 985 still < 1000 |
| 4 | D5: grant `CAP_SYS_ADMIN CAP_SYS_CHROOT` to the install-transaction unit (vs removing `chroot` from the install path) | product authority, `POSTR1-P5-INSTALLER-CHROOT-PRIVILEGE-FIX` | EPERM gone on the product path (this report) |
| 5 | Test-scope rule: systemd guards evaluate directive lines, not whole-file text | `POSTR1-P5-INSTALLER-SVC-TEST-SCOPE` (test file only) | comment rewords can no longer false-RED the gate |
| 6 | Honest-RED preservation (no predicate weakening/waiving/proxying, no fixture hacks, append-only ledgers, T3-P stays OPEN until 9/9) | every V12 brief + reviewers | V12G verdict is trustworthy *because* RED was preserved |
| 7 | Poisoned session `ses_f5b046…` abandoned; same-session resume must not be retried | mechanical rule + recovery finding | future attempts start cold |
| 8 | R1 finished with RED end-state (no invented D6 graph) | parent per completion-candidate rule | this report is the handoff, not a hidden plan |

---

## 7. Decisions YOU must take (the actual fork)

### Decision 1 — D6 repair side (blocking; everything else waits)

**Option A — release payloads become full Debian systems carrying apt/dpkg.**

- *What changes:* the mint (`open_bundle_payload_stream` inputs / bundle creation)
  builds a real release image filesystem instead of the current 64 MiB
  `{etc,lost+found,run,var}` payload; `chroot <slot> apt-get` then has something to execute.
- *Touches:* bundle/mint composition + builders, possibly `build/*` image pipeline;
  the install flow itself stays as-is.
- *Consequences:* **1 GiB slot-capacity/footprint impact** — a full Debian root is
  one to two orders of magnitude larger than 64 MiB; the 985 MiB installed footprint
  (already above the 800 preferred line, 15 MiB under the 1000 hard line) must be
  re-measured and re-accepted, and slot sizing (1 GiB nominal) may need architecture
  review per the >1250 rule's spirit. Release-image build becomes a real methodology
  (debootstrap/multistrap-equivalent provenance, signing, determinism) with its own
  C0 budget line.
- *Risk:* footprint/capacity blowout; longer builds; more to sign/verify.
- *Benefit:* install flow untouched; conceptually "the slot really is a Debian system".

**Option B — the install flow stops assuming `apt-get` inside a payload-only slot.**

- *What changes:* `src/greia_installer` (notably `fresh_ab_install.py` stream/finalize
  ordering + `hardware_support_install.py` 3 chroot legs + `device_seams.py:143`) and
  `src/greia_platform` (slot writer/finalizer contracts), plus contract tests
  (`test_install_transaction_service` 38, `test_installer_hardware_support_service` 3,
  `test_installer_unit_contract` 19, gate-closure suites), possibly
  `tools/greia_update.py` / `build/*`.
- *Candidate shapes (your architects choose, not this report):* pre-install firmware
  into the payload at mint time (pool-side `apt` on the host, not in-slot); or ship a
  static firmware-drop + manifest instead of `apt-get`; or run the hardware-support
  step on the host against the slot mount (no `chroot`) with strict path scoping.
- *Consequences:* real source change with contract-test updates; the D5 capability
  grant stays correct regardless (harmless if `chroot` legs shrink); no slot-size
  blowout — footprint likely *falls*.
- *Risk:* design work + test churn; must preserve fail-closed behavior and the
  single-writer/finalizer ownership reviewers explicitly praised.
- *Benefit:* keeps the 64 MiB payload methodology and the C0 budget; fixes the
  actual category error (payload-only slot ≠ Debian system).

**Recommendation (advisory, not authority):** Option B, on footprint and honesty
grounds — the slot *is* a payload, and pretending it is a Debian system just to feed
`apt-get` mortgages the 1000 MiB hard line for an install-time convenience. But this
is genuinely your call: if release payloads are *supposed* to become full systems for
other reasons (offline package availability, recovery), say so now, because it
redefines the mint — do not let it happen accidentally as a D6 side effect.

### Decision 2 — footprint posture (do together with Decision 1)
985 MiB passes <1000 but holds only 15 MiB of margin with the preferred ≤800 line
already breached. If you take Option A, re-accept the C0 budget explicitly *before*
the rebuild (measure the accepted delta like D4). If Option B, keep the 985 line as
the ceiling the repair must not breach.

### Decision 3 — T3-P gating discipline (no decision needed — keep the rule)
T3-P is marked DONE **iff** a future closure run goes 9/9 GREEN on one full orbiter
product-unit lifecycle. V12G correctly did not. Keep it that way; the rule is what
makes the RED trustworthy.

### Decision 4 — lane hygiene ownership (approve the cleanup list, §8.3)
Ephemeral key/sudoers, residual images, and pre-existing stuck loops are still on
orbiter. Approve their removal (or explicitly retain them) so the V12H lane starts clean.

---

## 8. Next moves — concrete sequence once you decide D6

1. **Decide A vs B** (§7) and record it as product/build authority (one paragraph in
   `HANDOVER.md` + the remediation-plan ledger — append-only, never rewriting §25).
2. **New repair task** (frozen brief, Allowed changes covering the chosen side):
   - A-side: mint/build-side brief (payload composition, signing, footprint proof).
   - B-side: `src/greia_installer` + `src/greia_platform` + contract-test brief
     (drop/relocate the in-slot-`apt-get` assumption, preserve fail-closed +
     single-writer ownership, update the 92-test surface + `make verify`).
3. **Official rebuild** from the repair HEAD through the production builders
   (fresh key/mint, `GREIA_AB_*` on the sudo line, SHA-bound archive — the V12G
   procedure is the template; never reuse images not bound to the tested HEAD).
4. **V12H closure re-run**: single full `run_gate_p5_closure_product()` with seeded
   `d31_fn` + P5.4 baseline + positive control, on the orbiter lane, docs-append-only
   on red. T3-P DONE iff 9/9 GREEN.
5. **Evidence bar for V12H** (demand exactly what V12G delivered): SHA-bound
   artifacts; built-artifact loop/unsquashfs proof (profile, crypto both levels,
   caps, socket wants); genuine product-path `TimeoutExpired`-or-green closure log;
   journal-to-console diag on disposable copies only; slot forensics if the install
   leg fails again; 92-test surface + `make verify` if source changed; no fixture hacks.

### 8.1 What NOT to do
- Do not re-run closure against the current image hoping D6 disappears (deterministic).
- Do not inject `apt-get` into a clone mid-run (harness substitution — the V12E rule).
- Do not resume `ses_f5b046…` (poisoned, abandoned).
- Do not `umount -R` a build chroot with host bind mounts (V12D lesson).
- Do not mark T3-P DONE on partial greens or transcript-only evidence.

### 8.2 Orbiter residue to clean (owner/parent)
- `/tmp/greia-p5-v12g5-*`, `/tmp/greia-p5-out-v12g5/`, `/tmp/v12g5-diag-*`
  (run image 1320157184 B, clones, driver, diag copies, slot-A mount sources);
- ephemeral key (`600`) + sudoers entry; bare `/dev/loop39` + `/dev/loop43` nodes
  (unattached kernel/udev residue after clean `losetup -d`); pre-existing stuck
  deleted-file loops (left untouched throughout — verify with `losetup -a` after a
  console reboot if the lane misbehaves).
- Concise evidence is already in-repo:
  `TBag/runs/R1/phases/postr1/tasks/POSTR1-P5-GATE-CLOSURE-V12G/attempts/implementer-5/`
  (`closure.log`, `diag-execute-serial.log`, `v12g5-status.json`, report).

---

## 9. Uncertainty register (what is NOT claimed)

- Full `make verify` (~500 s) was not re-run on V12G (no source changed; reviewer
  judged the 92-test surface + log/source tracing sufficient for a docs-only delta).
  V12H **must** run it if source changes (it will, on either D6 side).
- The slot-byte listing (`{etc,lost+found,run,var}`, no `/usr`) is recorded orbiter
  evidence corroborated by transcript/status; the reviewer did not re-mount it from
  the read-only view. The verdict does not depend on re-mounting (ENOENT + source
  ordering are sufficient), but V12H should re-capture forensics if the install leg
  fails again.
- Update/boot-health/recovery/boot-perf legs, D31 seed, P5.4 live record, RC-4 map,
  identity records: unexecuted by red necessity in V12G — nothing claimed, correctly
  carried, owned by the successor.
- `HANDOVER.md` §51's "next exact implementation task `POSTR1-P1-INSTALLER-RED`"
  line predates the V12E–V12G product-composition sequence and the §25 D6 record;
  the header + §25 (T3-P OPEN/BLOCKING, D6 decision required before any further
  closure re-run) govern. Reconcile that stale pointer when you issue the D6 repair
  task rather than letting two "next" lines coexist.

---

## 10. Evidence map (exact locations)

- Implementer verdict + proof:
  `TBag/runs/R1/phases/postr1/tasks/POSTR1-P5-GATE-CLOSURE-V12G/attempts/implementer-5/`
  (`report.md`, `closure.log:3-4` positive control + `:5-28` real 1200 s timeout,
  `diag-execute-serial.log:75-127` traceback, `v12g5-status.json` SHAs,
  `worker.log` 936 KB transcript, `scope-diff.json`/`evidence-gate.json` 3 docs-only files).
- Reviewer endorsement + second-pass verification:
  `…/attempts/reviewer-1/report.md` (92/92 re-run, source tracing, SHA consistency,
  T3-P-open confirmation).
- Runtime saga + cold-retry justification: `…/attempts/recovery-1/report.md`
  (implementer-1 retirement `-15`/`confirmed-silent-after-attempt-deadline`;
  attempts 2–4 single `APIError 400 encrypted_content` each; `RESUME` cold).
- Run record: `TBag/runs/R1/run.json` (`status: completed` 2026-09-15T16:01 UTC).
- Product state routing: `HANDOVER.md` header + §§16–25 (V11→V12G chain), especially
  §25 (V12G/D6); active plan
  `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`
  (V12G ledger) + `docs/plans/GREIA_BOOT_INSTALL_LIFECYCLE_TAKEOVER_2026-09-08.md`
  (V12G note).
- Key SHAs (V12G): HEAD `98b06079…`, tree `7657e5cb`, archive `bd8dc86d…`, image
  `3d3a01de…` (1320157184 B), bundles seq20 `c66d46bc…` / seq21 `5e2d611d…` /
  seq23 `1526ce11…`, driver `c4d9cd07…`; D5 caps at
  `build/installer-overlay/etc/systemd/system/greia-install-transaction.service:72-73`;
  D4 selection at `build/profiles/acer-aspire-one-i386-ab.toml:46,48`; gate owners at
  `tools/x8_qemu/gate_p5.py:49,233,389,703`.

---

*End of report. Bottom line: D5 is fixed and proven; D6 is the entire ballgame now.
Pick A or B, and the next closure run can be green. Until then, everything RED below
V12G is the system telling the truth.*
