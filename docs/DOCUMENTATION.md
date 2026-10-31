# Greia documentation authority and navigation

**Status:** maintained public documentation map · **Reviewed:** 2026-10-31

Greia distinguishes public project contracts from private maintainer coordination. This document tells contributors which source of truth to trust without exposing owner-specific operational records.

## Authority order

1. **Implemented behavior:** checked-in code, manifest schemas, package contracts and tests are the most precise statement of the current implementation.
2. **Accepted architecture:** [ADRs](adr/) document selected architectural invariants. An ADR does not by itself prove that a future capability has shipped.
3. **Product and child experience:** [product requirements](product/) express expected behavior; [design guides](design/) describe UI, accessibility, art and interaction.
4. **Technical implementation guides:** [architecture](architecture/), [engineering](engineering/) and [developer manuals](development/) explain how to work on the platform.
5. **Contributor and agent rules:** [AGENTS.md](../AGENTS.md), [CONTRIBUTING.md](../CONTRIBUTING.md), and [agent skill index](agents/README.md) govern contributions and evidence claims.
6. **User-facing instructions:** [user documentation](user/README.md) is the source for installation and Parents App guidance for families.

When documents differ, prefer the owner of the relevant fact and correct stale derived guidance; do not treat an aspirational proposal as implemented behavior.

## What belongs in the public tree

- Reproducible build and installation instructions.
- Architecture decisions, portable interfaces and package/language authoring guides.
- Generic testing procedures and a maintained hardware support matrix.
- Licensing, trademark, privacy, security and contributor policies.
- Factual limits and known restrictions stated without secrets or private infrastructure.

## What stays out

- Machine-local network addresses, SSH credentials, private infrastructure specifics and personal paths.
- Owner/agent handovers, task queues, dated implementation journals and internal release scheduling.
- Unapproved financial proposals, pricing strategies and speculative business arrangements.
- Unlicensed or rights-uncleared media and personal test data.

Older documents may remain accessible through public Git history. That is not secure archival storage. Sensitive credentials previously published must be rotated; deleting them from a working tree does not revoke them.

## Important entry points

[Project README](../README.md) · [Documentation index](README.md) · [Build an image](development/BUILD_A_GREIA_IMAGE.md) · [Create an Activity](development/CREATE_AN_ACTIVITY.md) · [Add a language](development/ADD_A_GREIA_LANGUAGE.md) · [Licensing](governance/LICENSING_AND_TRADEMARK.md) · [NOTICE](../NOTICE.md).

Documentation-only changes should keep these entry points, references and authority statements consistent. Public release status must be established by actual tests, rights clearance and owner approval, not by an old internal checkpoint.
