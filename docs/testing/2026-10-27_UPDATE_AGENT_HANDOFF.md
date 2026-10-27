# Historical update-agent handoff — 2026-10-27

**Status: COMPLETED DIAGNOSTIC / SUPERSEDED EXECUTION INSTRUCTIONS.**

This document formerly contained a 264-line, single-stage procedure using frozen `1275e0be1` guest artifacts and reviewed `78f07861` host tooling, plus an obsolete `1275..HEAD` source-difference gate. Those shell commands are **not** the current way to test Greia updates and have been removed to prevent accidental re-execution. The former procedure remains in Git history at the parent of the 2026-10-27 workflow-simplification commit.

**The diagnostic actually ran.** The installed A/B updater refused staging because it could not observe active `sda2` capacity. There was no B write/arm/boot, and the cause is now known at the production error boundary. See:

- [Captured production diagnostic](../reviews/2026-10-27_AB_OLD_RELEASE_STAGE_DIAGNOSTIC_RESULT.md).
- [Source-path analysis and hypotheses](../reviews/2026-10-27_AB_OLD_RELEASE_STAGE_REFUSAL_ANALYSIS.md).
- [Current single update implementation and Linux acceptance work order](GREIA_UPDATE_RELEASE_ACCEPTANCE.md).

Earlier source snapshots temporarily added a one-time receiver bridge to
handle the frozen 1275 development image. **That experiment is retired.** The
owner confirmed Greia has never been released, so historical receivers are
not supported update targets. The bridge module, CLI and dedicated tests
were deleted. See [current package acceptance](2026-10-27_LANGUAGE_UPDATE_PACKAGE_ACCEPTANCE.md).


**Current owner direction:** fix current `main` and run consolidated installed scenarios on disposable Linux/QEMU systems. No new source freezes, allowlist exceptions, redundant single-stage-only handoffs, or repeated old-guest diagnostics are prerequisites. Production update integrity, slot identity, atomicity, health/rollback and data preservation still apply.
