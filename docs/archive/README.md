# Greia engineering archive

**Status:** HISTORICAL. Nothing in this folder is current instruction.
**Created:** 2026-10-16, during the open-source cleanup.

This folder keeps the dated reviews, investigations and decision reports from
August–September 2026 that still teach something useful. The documents are
moved here verbatim: they are not rewritten, and their status lines, commit
SHAs and "next step" sections describe the moment they were written, not the
current project.

What was **not** kept: screenshots, capture evidence (JSON traces, logs,
checksums), one-off runbooks and test procedures for finished work, session
handovers and status snapshots. Those files remain in git history; find them
with `git log --all --diff-filter=D --name-only -- docs/`.

Archived documents may contain image links or cross-links to files that were
removed. A path such as `docs/reviews/X.md` in an older ledger entry now lives
at `docs/archive/reviews/X.md` if it appears below.

For the current state of the project, read `README.md`, `HANDOVER.md` and
`docs/DOCUMENTATION.md` instead.

## Language-support history

| Document | Lesson |
|---|---|
| [plans/LANGUAGE_SUPPORT_TIERS_PROPOSAL_2026-09-27.md](plans/LANGUAGE_SUPPORT_TIERS_PROPOSAL_2026-09-27.md) | The old declared twelve-language set overstated actual text and voice coverage. Its staged tiers were superseded by the owner-approved EN/IT/ES/FR rollout and later per-language manifest discovery; follow `docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md` and `docs/development/ADD_A_GREIA_LANGUAGE.md` for current behavior. |

## Boot, installation and hardware

| Document | Lesson |
|---|---|
| [reviews/2026-08-15_HARDWARE_ENABLEMENT_IMPLEMENTATION_REVIEW.md](reviews/2026-08-15_HARDWARE_ENABLEMENT_IMPLEMENTATION_REVIEW.md) | Let the kernel bind drivers and Debian metadata choose firmware; target package plans fail closed and never rely on a "missing firmware" signal alone. |
| [reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md](reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md) | Ten reusable failure classes from the first real installs: build-host state is not target truth, media identity and payload must not drift apart, appliance services must not inherit terminal semantics, and fixes documented in a log must also land in the build overlay. |
| [reviews/2026-08-20_ACER_INSTALLER_BOOT_REGRESSION.md](reviews/2026-08-20_ACER_INSTALLER_BOOT_REGRESSION.md) | Never remove observable boot output or change firmware-sensitive boot art or USB writing without physical proof; keep verification out of the writer itself. |
| [reviews/2026-09-27_ACER_AB_GRUB_INSTALLER_PHYSICAL_BOOT_FAILURE.md](reviews/2026-09-27_ACER_AB_GRUB_INSTALLER_PHYSICAL_BOOT_FAILURE.md) | A boot path already recorded as incompatible was flashed, and a previously removed diagnostic-suppression change had crept back. Check recorded hardware contracts and git history before flashing. |
| [handovers/2026-09-27_SESSION04_ACER_UNIVERSAL_SETUP_HANDOFF.md](handovers/2026-09-27_SESSION04_ACER_UNIVERSAL_SETUP_HANDOFF.md) | Separates the three boot responsibilities (universal Setup medium, installed x86 disk, Raspberry Pi) and explains why one universal Setup image was chosen. |
| [testing/2026-09-24_SESSION04_INSTALL_EXECUTE_FAILURE_DIAGNOSIS.md](testing/2026-09-24_SESSION04_INSTALL_EXECUTE_FAILURE_DIAGNOSIS.md) | How a silent install failure was traced over 13 instrumented runs to apt's privilege drop failing inside the service sandbox. |
| [testing/2026-09-25_SESSION04_INSTALL_EXECUTE_ROOT_CAUSE_AND_DECISION.md](testing/2026-09-25_SESSION04_INSTALL_EXECUTE_ROOT_CAUSE_AND_DECISION.md) | The narrow fix: keep the sandbox, add only `CAP_SETUID`/`CAP_SETGID`, and run the service through a thin separate entrypoint. |
| [testing/2026-09-25_SESSION04_APT_OWNERSHIP_DECISION.md](testing/2026-09-25_SESSION04_APT_OWNERSHIP_DECISION.md) | An apt `chown` warning was not the fatal error. Do not widen capabilities on an unproven inference. |
| [plans/GREIA_GATE_P5_V12G_CLOSURE_DECISION_REPORT_2026-09-15.md](plans/GREIA_GATE_P5_V12G_CLOSURE_DECISION_REPORT_2026-09-15.md) | A chain of shipped-product defects only surfaced on the real product path; each fix moved the install one stage further. Source tests alone did not reveal them. |
| [reviews/2026-08-25_INSTALLED_ACTIVITY_RESILIENCE_HARDENING.md](reviews/2026-08-25_INSTALLED_ACTIVITY_RESILIENCE_HARDENING.md) | Cleanup code placed at the wrong privilege boundary silently failed on the read-only installed tree; run it as a narrow privileged pre-start helper. |
| [reviews/2026-08-24_ACER_MICROPHONE_PHYSICAL_ACCEPTANCE.md](reviews/2026-08-24_ACER_MICROPHONE_PHYSICAL_ACCEPTANCE.md) | SDL only opens `hw:`/`sysdefault:`/`default:` devices, so the platform injects the composed ALSA route; Activities never pick hardware. |

## Display, session and trusted Home (R7)

| Document | Lesson |
|---|---|
| [reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md](reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md) | Who owns the seat, DRM master, input devices and visible surface across Shell ↔ Activity transitions; serial KMSDRM ownership versus a tiny Greia-owned compositor. |
| [reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md](reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md) | Where X11 leaked beyond its backend and the order for removing it. Choose a compositor only on measured evidence. |
| [reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md](reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md) | Activities must not know the display backend. Recurring anti-patterns (Activity-owned chrome, ESC exits, direct device events), and why backend independence must not add an abstraction tax. |
| [reviews/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_INVENTORY.md](reviews/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_INVENTORY.md) | Which X-specific code is acceptable inside the compatibility adapter, and which provisional debt is deliberately left visible. |
| [reviews/2026-08-29_R7_R73_ACTIVITY_CHROME_MIGRATION_TRANCHE.md](reviews/2026-08-29_R7_R73_ACTIVITY_CHROME_MIGRATION_TRANCHE.md) | Moving Activities off self-drawn Home. Code search with incomplete results is not proof, so a repository-local audit tool owns that evidence. |
| [reviews/2026-08-29_R7_R73_SOURCE_GATE_FAILURE_AND_REMEDIATION.md](reviews/2026-08-29_R7_R73_SOURCE_GATE_FAILURE_AND_REMEDIATION.md) | Separate stale tests from real regressions; substring checks over source code gave false positives and were replaced by AST checks. |
| [reviews/2026-08-30_R7_R73_HOME_OVERLAY_POST_MODERNIZATION_CORRECTION.md](reviews/2026-08-30_R7_R73_HOME_OVERLAY_POST_MODERNIZATION_CORRECTION.md) | Trusted Home must fail loudly and survive dirty-rectangle updates. |
| [reviews/2026-08-31_R7_ACER_WRITING_BLACK_SURFACE_ROOT_CAUSE_AND_FIX.md](reviews/2026-08-31_R7_ACER_WRITING_BLACK_SURFACE_ROOT_CAUSE_AND_FIX.md) | Presenting an unused reference canvas overwrote the real frame. Give every frame one surface owner. |
| [reviews/2026-08-31_R7_SIMULATOR_RUNTIME_INTEGRATION_REJECTION_AND_CORRECTION.md](reviews/2026-08-31_R7_SIMULATOR_RUNTIME_INTEGRATION_REJECTION_AND_CORRECTION.md) | Test Activities through the real script-mode launch path; protected Home input must not depend on the Activity pumping its event queue. |
| [reviews/2026-09-01_R7_SHELL_FOCUS_RETURN_DEFECT_AND_FIX.md](reviews/2026-09-01_R7_SHELL_FOCUS_RETURN_DEFECT_AND_FIX.md) | Keyboard focus must be repaired on every Activity return, not once at window creation. |
| [reviews/2026-09-01_R7_CURRENT_HEAD_USAGE_LIMIT_LIFECYCLE_REVIEW.md](reviews/2026-09-01_R7_CURRENT_HEAD_USAGE_LIMIT_LIFECYCLE_REVIEW.md) | A usage-ledger lock failure must fail closed, and a child whose time is used up should never see a fake launch. |
| [reviews/2026-09-02_R7_SYSTEM_CONTROL_TRANSACTION_AND_BUFFERED_KEY_REVIEW.md](reviews/2026-09-02_R7_SYSTEM_CONTROL_TRANSACTION_AND_BUFFERED_KEY_REVIEW.md) | Relative updates (volume +5) must read, modify and write inside one lock; already-buffered Xlib events can stall behind `select()`. |

## Platform architecture and input

| Document | Lesson |
|---|---|
| [reviews/2026-08-08_ARCHITECTURE_DEEP_REVIEW_V0_13.md](reviews/2026-08-08_ARCHITECTURE_DEEP_REVIEW_V0_13.md) | Authority placement matters more than naming: the sandbox isolated profiles from each other but not Activities within one profile. |
| [reviews/2026-08-08_ACTIVE_PLAN_AUDIT_AND_CORRECTION.md](reviews/2026-08-08_ACTIVE_PLAN_AUDIT_AND_CORRECTION.md) | Verify claims against source before planning. Capabilities are not permissions, effective grants need a real broker, and an invented generic "Resource Service" was retracted. |
| [reviews/2026-08-15_INPUT_CONTROLLER_FOUNDATION_ADVERSARIAL_REVIEW.md](reviews/2026-08-15_INPUT_CONTROLLER_FOUNDATION_ADVERSARIAL_REVIEW.md) | Keyboard events handled twice, repeat timing belongs to platform policy, and controller ownership stops at the Activity boundary. |
| [reviews/2026-08-15_UBUNTU_LEGACY_X86_SOURCE_GATE_FAILURE_AND_REPAIR.md](reviews/2026-08-15_UBUNTU_LEGACY_X86_SOURCE_GATE_FAILURE_AND_REPAIR.md) | Distribution Pygame builds may omit SDL2 controller constants; classify each failure as a real defect or a stale test before fixing. |
| [reviews/2026-08-16_UBUNTU_SOURCE_GATE_8D05FBB_SHELL_INPUT_REPAIR.md](reviews/2026-08-16_UBUNTU_SOURCE_GATE_8D05FBB_SHELL_INPUT_REPAIR.md) | A floating-point boundary bug in analog repeat, and a test that bypassed the compatibility layer it was meant to cover. |
| [reviews/2026-08-16_UBUNTU_ACTIVITY_BYTECODE_VALIDATION_FIX.md](reviews/2026-08-16_UBUNTU_ACTIVITY_BYTECODE_VALIDATION_FIX.md) | Cached bytecode inside Activity folders fails validation by design; clean it before validating. |
| [reviews/2026-08-24_SHARED_ACTIVITY_PAGINATION_REVIEW.md](reviews/2026-08-24_SHARED_ACTIVITY_PAGINATION_REVIEW.md) | Discrete pages are not a sliding window; one shared pager serves every Collection. |

## Activity Simulator

| Document | Lesson |
|---|---|
| [reviews/2026-08-19_ACTIVITY_SIMULATOR_ADVERSARIAL_REVIEW.md](reviews/2026-08-19_ACTIVITY_SIMULATOR_ADVERSARIAL_REVIEW.md) | The simulator must inject only synthetic variation points and never duplicate production composition (see ADR 0029). |
| [reviews/2026-08-19_ACTIVITY_SIMULATOR_HARDENING_RESPONSE.md](reviews/2026-08-19_ACTIVITY_SIMULATOR_HARDENING_RESPONSE.md) | How each finding was fixed by making the simulator thinner rather than adding simulator copies of Greia services. |

## Activities and product

| Document | Lesson |
|---|---|
| [reviews/2026-08-10_CORE_CREATION_SOURCE_TRANCHE.md](reviews/2026-08-10_CORE_CREATION_SOURCE_TRANCHE.md) | Undo memory models, save-failure transitions and creation transactions for Writing and Painting. |
| [reviews/2026-08-23_CLINICA_CUCCIOLI_ARCHITECTURE_CALIBRATION.md](reviews/2026-08-23_CLINICA_CUCCIOLI_ARCHITECTURE_CALIBRATION.md) | Splitting a 33 KB single-file Activity: runtime-adapter and import-mode pitfalls, and tests that encoded the old file layout. |
| [reviews/2026-09-02_RECENT_COMMIT_CLEANUP_PARENT_AND_TODDLER_RUNTIME.md](reviews/2026-09-02_RECENT_COMMIT_CLEANUP_PARENT_AND_TODDLER_RUNTIME.md) | Activities must not copy platform pointer or Home logic, audio synthesis stays out of input hot paths, and demo behaviour must not leak into production. |
| [reviews/2026-09-08_LAUNCHER_PRODUCT_PERFORMANCE_AND_AUTHORING_REVIEW.md](reviews/2026-09-08_LAUNCHER_PRODUCT_PERFORMANCE_AND_AUTHORING_REVIEW.md) | Caches that remember "missing" go stale after updates, and duplicated Shell event loops drift apart. |
| [plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/README.md](plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/README.md) | The pedagogical research basis and portfolio-gap analysis behind ten early-learning Activities (per-session files removed). |
| [plans/2026-08-06_PHASE0_BOOTABLE_VERTICAL_SLICE.md](plans/2026-08-06_PHASE0_BOOTABLE_VERTICAL_SLICE.md) | The original Phase-0 hard gates that still shape the product contracts in `AGENTS.md`. |

## Encyclopedia

| Document | Lesson |
|---|---|
| [reviews/2026-08-27_ENCYCLOPEDIA_V01_POST_BUILD_DRIFT_REVIEW.md](reviews/2026-08-27_ENCYCLOPEDIA_V01_POST_BUILD_DRIFT_REVIEW.md) | A locale audio schema mismatch and mixed narration formats; tests should compare the authoring and runtime catalogues directly instead of a third copied list. |
| [reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md](reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md) | Programmer-drawn primitives look unfinished; pages should consume the shared visual system rather than each drawing its own subject. |
| [reviews/2026-08-31_R7_CURRENT_HEAD_SOURCE_GATE_REJECTION_AND_EARTH_CACHE_FIX.md](reviews/2026-08-31_R7_CURRENT_HEAD_SOURCE_GATE_REJECTION_AND_EARTH_CACHE_FIX.md) | Image decoding and scaling crept back into a page's per-frame path; the performance tests caught it. |
| [reviews/2026-08-31_R7_SECOND_SOURCE_REJECTION_MAGNET_TYPOGRAPHY_FIX.md](reviews/2026-08-31_R7_SECOND_SOURCE_REJECTION_MAGNET_TYPOGRAPHY_FIX.md) | Use the bounded typography owner; never construct fonts inside a page. |

## Visual art, voice and evidence quality

| Document | Lesson |
|---|---|
| [reviews/visual/2026-08-21_authoring-kit-variation/PRIMARY_REVIEW.md](reviews/visual/2026-08-21_authoring-kit-variation/PRIMARY_REVIEW.md) | "Enlarged icon art": low-resolution readability constrains simplification; it does not license simplistic source masters. |
| [reviews/visual/2026-08-21_authoring-kit-v03-corrective/PRIMARY_REVIEW.md](reviews/visual/2026-08-21_authoring-kit-v03-corrective/PRIMARY_REVIEW.md) | Swapping circles for more complex Bézier paths does not change the visual read on its own. |
| [reviews/visual/2026-08-21_generic-authoring-library-consolidation/PRIMARY_REVIEW.md](reviews/visual/2026-08-21_generic-authoring-library-consolidation/PRIMARY_REVIEW.md) | Harvest every existing source pool before declaring library gaps. |
| [reviews/visual/2026-08-21_forest-meadow-base-pack-reauthoring/PRIMARY_REVIEW.md](reviews/visual/2026-08-21_forest-meadow-base-pack-reauthoring/PRIMARY_REVIEW.md) | Review evidence must show the complete mapped pack, and self-reviews tend to overclaim whole-pack replacement. |
| [reviews/visual/2026-08-21_clinic-care-base-pack-reauthoring/PRIMARY_REVIEW.md](reviews/visual/2026-08-21_clinic-care-base-pack-reauthoring/PRIMARY_REVIEW.md) | Re-authored assets are often different useful objects or states, not one-for-one replacements; keep both. |
| [reviews/visual/2026-08-21_workshop-base-pack-reauthoring/PRIMARY_REVIEW.md](reviews/visual/2026-08-21_workshop-base-pack-reauthoring/PRIMARY_REVIEW.md) | The same replacement-versus-variant lesson for the Workshop pack: deleting a baseline variant shrinks the toolbox. |
| [reviews/visual/2026-08-22_canonical-cast-v01-runtime-simulator/OWNER_REVIEW.md](reviews/visual/2026-08-22_canonical-cast-v01-runtime-simulator/OWNER_REVIEW.md) | A failed rendition must not be retried every frame; remember failures in a bounded cache. |
| [reviews/visual/2026-08-22_canonical-cast-v01-runtime-recheck/OWNER_REVIEW_CAPTURE_INTEGRITY.md](reviews/visual/2026-08-22_canonical-cast-v01-runtime-recheck/OWNER_REVIEW_CAPTURE_INTEGRITY.md) | Evidence captures must show what their labels claim; isolate each scenario before capturing it. |
| [reviews/performance/2026-08-22_launcher-pacing-dirty-redraw/OWNER_REVIEW.md](reviews/performance/2026-08-22_launcher-pacing-dirty-redraw/OWNER_REVIEW.md) | Performance-measurement pitfalls: too-short samples, latency windows that exclude idle waits, internally inconsistent memory figures. |
| [reviews/voice/2026-08-23_CHARACTER_AND_PEDAGOGICAL_SPEECH_FINDINGS.md](reviews/voice/2026-08-23_CHARACTER_AND_PEDAGOGICAL_SPEECH_FINDINGS.md) | If the sound itself is what is being taught, use deterministic pedagogical speech; character voices carry content, not pronunciation truth. |

## Documentation

| Document | Lesson |
|---|---|
| [reviews/2026-09-02_PUBLIC_REPOSITORY_DOCUMENTATION_DEEP_DIVE.md](reviews/2026-09-02_PUBLIC_REPOSITORY_DOCUMENTATION_DEEP_DIVE.md) | Living entry points slowly absorb history. Give every document class one job and retire stale ones explicitly. |
